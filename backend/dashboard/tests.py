"""Dashboard tiles must read real sale / ROI / reward ledgers."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from associates.models import Associate
from commissions.models import CommissionEntry, CommissionRun
from dashboard.views import _income_breakdown_tiles, _wallet_map
from genealogy.services import GenealogyService
from wallets.models import Wallet
from wallets.services import WalletService

User = get_user_model()


class DashboardIncomeTileTests(TestCase):
    def test_tiles_split_sale_l1_l2_and_roi(self):
        user = User.objects.create_user(username="joydash", password="x", email="joydash@t.test")
        a = Associate.objects.create(
            user=user,
            associate_id="JOYDASH01",
            referral_code="RDASH01",
            mobile="9000000001",
            status=Associate.Status.ACTIVE,
        )
        GenealogyService.ensure_root(a)
        WalletService.ensure_wallets(a)
        run_l = CommissionRun.objects.create(
            run_type=CommissionRun.RunType.LEVEL, status=CommissionRun.Status.COMPLETED
        )
        run_r = CommissionRun.objects.create(
            run_type=CommissionRun.RunType.ROI, status=CommissionRun.Status.COMPLETED
        )
        CommissionEntry.objects.create(
            run=run_l,
            beneficiary=a,
            level=1,
            percent=Decimal("5"),
            sale_amount=Decimal("220000"),
            amount=Decimal("11000"),
            wallet_type=Wallet.WalletType.INCOME,
            reference="SALE-L1",
            status=CommissionEntry.Status.CREDITED,
        )
        CommissionEntry.objects.create(
            run=run_l,
            beneficiary=a,
            level=2,
            percent=Decimal("2.5"),
            sale_amount=Decimal("220000"),
            amount=Decimal("5500"),
            wallet_type=Wallet.WalletType.INCOME,
            reference="SALE-L2",
            status=CommissionEntry.Status.CREDITED,
        )
        CommissionEntry.objects.create(
            run=run_r,
            beneficiary=a,
            level=1,
            percent=Decimal("5"),
            sale_amount=Decimal("220000"),
            monthly_return_amount=Decimal("2200"),
            amount=Decimal("110.00"),
            wallet_type=Wallet.WalletType.ROI,
            reference="ROI-L1",
            status=CommissionEntry.Status.CREDITED,
        )
        tiles = _income_breakdown_tiles(a)
        self.assertEqual(tiles["referral_income"], Decimal("11000"))
        self.assertEqual(tiles["level_income"], Decimal("5500"))
        self.assertEqual(tiles["sp_income"], Decimal("110.00"))
        self.assertEqual(tiles["roi_income"], Decimal("110.00"))

    def test_roi_wallet_tile_hides_buyer_self_2200(self):
        user = User.objects.create_user(username="joyhid", password="x", email="joyhid@t.test")
        a = Associate.objects.create(
            user=user,
            associate_id="JOYHID01",
            referral_code="RHID01",
            mobile="9000000011",
            status=Associate.Status.ACTIVE,
        )
        GenealogyService.ensure_root(a)
        WalletService.ensure_wallets(a)
        WalletService.credit(
            associate=a,
            wallet_type=Wallet.WalletType.ROI,
            amount=Decimal("2200.00"),
            reference="MRI-aaaa-M1",
            narration="Monthly ROI M1",
        )
        WalletService.credit(
            associate=a,
            wallet_type=Wallet.WalletType.ROI,
            amount=Decimal("110.00"),
            reference="MRI-aaaa-M1-L1",
            narration="Level 1 ROI Income",
        )
        wallets = _wallet_map(a)
        self.assertEqual(wallets["roi"], Decimal("110.00"))


class DashboardRoiPerformanceTests(TestCase):
    def test_roi_performance_board_locks_above_qualified_directs(self):
        from configuration.models import PerformanceIncomePlan, PerformanceIncomeSlab
        from dashboard.views import _roi_performance_board

        user = User.objects.create_user(username="joyperf", password="x", email="joyperf@t.test")
        a = Associate.objects.create(
            user=user,
            associate_id="JOYPERF01",
            referral_code="RPERF01",
            mobile="9000000002",
            status=Associate.Status.ACTIVE,
        )
        GenealogyService.ensure_root(a)
        WalletService.ensure_wallets(a)
        plan, _ = PerformanceIncomePlan.objects.get_or_create(
            code="performance-10",
            defaults={"name": "Performance Income", "max_levels": 10, "is_active": True},
        )
        for level, pct in [
            (1, "5"),
            (2, "2.5"),
            (3, "2"),
            (4, "2"),
            (5, "1"),
            (6, "1"),
            (7, "0.5"),
            (8, "0.5"),
            (9, "0.25"),
            (10, "0.25"),
        ]:
            PerformanceIncomeSlab.objects.update_or_create(
                plan=plan,
                level=level,
                defaults={"percent": Decimal(pct), "required_directs": level, "is_active": True},
            )
        board = _roi_performance_board(a)
        self.assertEqual(board["qualified_directs"], 0)
        self.assertEqual(board["unlocked_level"], 0)
        self.assertTrue(all(not s["unlocked"] for s in board["slabs"]))


class DashboardSaleLevelTests(TestCase):
    def test_sale_level_board_unlocks_from_direct_sales(self):
        from configuration.models import LevelIncomePlan, LevelIncomeSlab
        from dashboard.views import _sale_level_board

        plan, _ = LevelIncomePlan.objects.get_or_create(
            code="direct-level",
            defaults={"name": "Direct Level Income", "max_levels": 5, "is_active": True},
        )
        for level, pct in [(1, "5"), (2, "2.5"), (3, "2"), (4, "1"), (5, "0.5")]:
            LevelIncomeSlab.objects.update_or_create(
                plan=plan,
                level=level,
                defaults={"percent": Decimal(pct), "is_active": True},
            )
        user = User.objects.create_user(username="joysale", password="x", email="joysale@t.test")
        a = Associate.objects.create(
            user=user,
            associate_id="JOYSALE01",
            referral_code="RSALE01",
            mobile="9000000003",
            status=Associate.Status.ACTIVE,
        )
        GenealogyService.ensure_root(a)
        WalletService.ensure_wallets(a)
        board = _sale_level_board(a)
        self.assertEqual(board["qualified_direct_sales"], 0)
        self.assertEqual(board["unlocked_level"], 0)
        self.assertEqual(len(board["slabs"]), 5)
        self.assertTrue(all(not s["unlocked"] for s in board["slabs"]))
