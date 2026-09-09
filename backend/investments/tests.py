"""Monthly ROI ₹2,200 + ROI-on-ROI upline (level % on base ROI)."""

from datetime import date
from decimal import Decimal
from hashlib import md5

from django.contrib.auth import get_user_model
from django.test import TestCase

from associates.models import Associate
from commissions.constants import FARHOUSE_SALE_AMOUNT
from commissions.models import CommissionEntry
from commissions.services import CommissionEngine
from configuration.models import LevelIncomePlan, LevelIncomeSlab, PerformanceIncomePlan, PerformanceIncomeSlab
from genealogy.services import GenealogyService
from investments.calc import roi_level_income
from investments.constants import MONTHLY_RETURN_AMOUNT
from investments.models import InvestmentContract
from investments.services import create_investment_contracts, process_monthly_return
from wallets.business import apply_investment_business
from wallets.models import Wallet
from wallets.services import WalletService

User = get_user_model()
SALE = FARHOUSE_SALE_AMOUNT


class MonthlyGrowthCommissionTests(TestCase):
    def setUp(self):
        level_plan, _ = LevelIncomePlan.objects.get_or_create(
            code="direct-level",
            defaults={"name": "Direct Level Income", "max_levels": 5, "is_active": True},
        )
        for level, pct in [(1, "5"), (2, "2.5"), (3, "2"), (4, "1"), (5, "0.5")]:
            LevelIncomeSlab.objects.update_or_create(
                plan=level_plan,
                level=level,
                defaults={"percent": Decimal(pct), "is_active": True},
            )
        perf, _ = PerformanceIncomePlan.objects.get_or_create(
            code="performance-10",
            defaults={"name": "Performance Income", "max_levels": 10, "is_active": True},
        )
        for level, pct, directs in [
            (1, "5", 1),
            (2, "2.5", 2),
            (3, "2", 3),
            (4, "2", 4),
            (5, "1", 5),
            (6, "1", 6),
            (7, "0.5", 7),
            (8, "0.5", 8),
            (9, "0.25", 9),
            (10, "0.25", 10),
        ]:
            PerformanceIncomeSlab.objects.update_or_create(
                plan=perf,
                level=level,
                defaults={
                    "percent": Decimal(pct),
                    "required_directs": directs,
                    "is_active": True,
                },
            )

    def _user(self, username: str) -> User:
        return User.objects.create_user(username=username, password="x", email=f"{username}@t.test")

    def _assoc(self, code: str, *, sponsor: Associate | None = None, active: bool = True) -> Associate:
        user = self._user(code.lower())
        mobile = f"{int(md5(code.encode()).hexdigest()[:9], 16) % 10**10:010d}"
        a = Associate.objects.create(
            user=user,
            associate_id=code,
            referral_code=f"R{code}"[:20],
            mobile=mobile,
            sponsor=sponsor,
            status=Associate.Status.ACTIVE if active else Associate.Status.INACTIVE,
            join_amount=SALE if active else Decimal("0"),
            personal_business=SALE if active else Decimal("0"),
            total_business=SALE if active else Decimal("0"),
        )
        if sponsor is None:
            GenealogyService.ensure_root(a)
        else:
            GenealogyService.attach_under_sponsor(a, sponsor, force=True)
        WalletService.ensure_wallets(a)
        return a

    def _seed_qualifying_directs(self, sponsor: Associate, needed: int, tag: str) -> None:
        have = CommissionEngine.growth_level(sponsor)
        extra = 0
        while have < needed:
            self._assoc(f"JOY{tag}{extra:02d}"[:16], sponsor=sponsor, active=True)
            extra += 1
            have += 1

    def test_investment_creates_contract_and_first_month_roi(self):
        root = self._assoc("JOYMROOT01")
        buyer = self._assoc("JOYMBUY001", sponsor=root, active=False)
        apply_investment_business(associate=buyer, amount=SALE, reference="INV-1")
        contracts = list(InvestmentContract.objects.filter(associate=buyer))
        self.assertEqual(len(contracts), 1)
        c = contracts[0]
        self.assertEqual(c.monthly_return, MONTHLY_RETURN_AMOUNT)
        self.assertEqual(c.months_paid, 1)

        roi = Wallet.objects.get(associate=buyer, wallet_type=Wallet.WalletType.ROI)
        self.assertEqual(roi.balance, Decimal("0.00"))
        income = Wallet.objects.get(associate=buyer, wallet_type=Wallet.WalletType.INCOME)
        self.assertEqual(income.balance, Decimal("0.00"))
        self.assertFalse(
            CommissionEntry.objects.filter(beneficiary=buyer, month_index=1, level=0).exists()
        )
        # Network L1: base ROI × 5% = ₹110
        growth = CommissionEntry.objects.get(
            beneficiary=root,
            month_index=1,
            level=1,
            wallet_type=Wallet.WalletType.ROI,
        )
        self.assertEqual(growth.amount, Decimal("110.00"))
        self.assertEqual(growth.monthly_return_amount, MONTHLY_RETURN_AMOUNT)
        self.assertEqual(growth.percent, Decimal("5.0000"))

    def test_network_level_2_gets_2_5_percent_of_base_roi(self):
        root = self._assoc("JOYMROOT02")
        mid = self._assoc("JOYMMID002", sponsor=root)
        self._seed_qualifying_directs(root, 2, "R2")
        buyer = self._assoc("JOYMBUY002", sponsor=mid, active=False)
        apply_investment_business(associate=buyer, amount=SALE, reference="INV-B2")
        # Root is network depth 2 → 2.5% of ₹2,200 = ₹55 (needs 2 qualified directs)
        e = CommissionEntry.objects.get(beneficiary=root, month_index=1, level=2, source_associate=buyer)
        self.assertEqual(e.percent, Decimal("2.5000"))
        self.assertEqual(e.amount, Decimal("55.00"))
        # Mid is depth 1 → 5% = ₹110
        mid_e = CommissionEntry.objects.get(beneficiary=mid, month_index=1, level=1, source_associate=buyer)
        self.assertEqual(mid_e.amount, Decimal("110.00"))

    def test_level_2_skipped_when_upline_has_one_direct(self):
        """Ineligible depth is skipped — no spillover of that % to anyone else."""
        root = self._assoc("JOYMROOT2S")
        mid = self._assoc("JOYMMID2S0", sponsor=root)
        buyer = self._assoc("JOYMBUY2S0", sponsor=mid, active=False)
        apply_investment_business(associate=buyer, amount=SALE, reference="INV-SKIP2")
        self.assertFalse(
            CommissionEntry.objects.filter(
                beneficiary=root,
                source_associate=buyer,
                level=2,
                wallet_type=Wallet.WalletType.ROI,
            ).exists()
        )
        mid_e = CommissionEntry.objects.get(
            beneficiary=mid,
            source_associate=buyer,
            level=1,
            wallet_type=Wallet.WalletType.ROI,
        )
        self.assertEqual(mid_e.amount, Decimal("110.00"))
        self.assertFalse(
            CommissionEntry.objects.filter(
                source_associate=buyer, level=2, wallet_type=Wallet.WalletType.ROI
            ).exists()
        )

    def test_three_directs_unlock_levels_1_to_3_only(self):
        root = self._assoc("JOYMULK003")
        for i in range(3):
            self._assoc(f"JOYMULD{i:02d}", sponsor=root)
        self.assertEqual(CommissionEngine.growth_level(root), 3)
        self.assertEqual(CommissionEngine.unlocked_performance_levels(root), 3)

        mid = self._assoc("JOYMULMID3", sponsor=root, active=True)
        mid.join_amount = Decimal("0")
        mid.personal_business = Decimal("0")
        mid.save(update_fields=["join_amount", "personal_business", "updated_at"])
        a = self._assoc("JOYMULA003", sponsor=mid)
        b = self._assoc("JOYMULB003", sponsor=a)
        self._seed_qualifying_directs(mid, 3, "M3")
        self._seed_qualifying_directs(a, 2, "A3")
        buyer = self._assoc("JOYMULBUY3", sponsor=b, active=False)
        apply_investment_business(associate=buyer, amount=SALE, reference="INV-3DIR")

        # root is depth 4 and only unlocked 1–3
        self.assertFalse(
            CommissionEntry.objects.filter(beneficiary=root, source_associate=buyer, level=4).exists()
        )
        paid_levels = set(
            CommissionEntry.objects.filter(
                source_associate=buyer, wallet_type=Wallet.WalletType.ROI, level__gte=1
            )
            .exclude(status=CommissionEntry.Status.VOIDED)
            .values_list("level", flat=True)
        )
        self.assertEqual(paid_levels, {1, 2, 3})

    def test_ten_level_chain_roi_on_roi_total(self):
        """Full 10-upline chain: total upline share = ₹330 on ₹2,200 base ROI."""
        chain = [self._assoc("JOYMCHAIN00")]
        for i in range(1, 11):
            chain.append(self._assoc(f"JOYMCHAIN{i:02d}", sponsor=chain[-1]))
        # chain[k] is depth (11-k) from buyer; each needs that many qualified directs.
        for i, ancestor in enumerate(chain):
            depth = 11 - i
            if 1 <= depth <= 10:
                self._seed_qualifying_directs(ancestor, depth, f"C{i:02d}")
        buyer = self._assoc("JOYMBUY010", sponsor=chain[-1], active=False)
        apply_investment_business(associate=buyer, amount=SALE, reference="INV-10L")

        entries = CommissionEntry.objects.filter(
            source_associate=buyer,
            wallet_type=Wallet.WalletType.ROI,
            level__gte=1,
        ).exclude(status=CommissionEntry.Status.VOIDED)
        self.assertEqual(entries.count(), 10)
        total = sum(e.amount for e in entries)
        self.assertEqual(total, Decimal("330.00"))
        for depth in range(1, 11):
            expected = roi_level_income(base_roi=MONTHLY_RETURN_AMOUNT, network_level=depth)
            row = entries.get(level=depth)
            self.assertEqual(row.amount, expected)

    def test_duplicate_month_not_double_paid(self):
        root = self._assoc("JOYMROOT03")
        buyer = self._assoc("JOYMBUY003", sponsor=root, active=False)
        apply_investment_business(associate=buyer, amount=SALE, reference="INV-DUP")
        c = InvestmentContract.objects.get(associate=buyer)
        process_monthly_return(c, as_of=date.today())
        self.assertEqual(
            CommissionEntry.objects.filter(
                source_associate=buyer, wallet_type=Wallet.WalletType.ROI, month_index=1, level=1
            ).count(),
            1,
        )
        self.assertFalse(
            CommissionEntry.objects.filter(beneficiary=buyer, level=0).exists()
        )
        c.refresh_from_db()
        self.assertEqual(c.months_paid, 1)
        roi = Wallet.objects.get(associate=root, wallet_type=Wallet.WalletType.ROI)
        first_balance = roi.balance
        process_monthly_return(c, as_of=date.today())
        roi.refresh_from_db()
        self.assertEqual(roi.balance, first_balance)

    def test_multiple_buyers_use_actual_genealogy_not_48(self):
        """Two ROI events → two L1 credits of ₹110. Never hardcoded ×48."""
        root = self._assoc("JOYMROOT48")
        b1 = self._assoc("JOYMBUY48A", sponsor=root, active=False)
        b2 = self._assoc("JOYMBUY48B", sponsor=root, active=False)
        apply_investment_business(associate=b1, amount=SALE, reference="INV-48A")
        apply_investment_business(associate=b2, amount=SALE, reference="INV-48B")
        entries = CommissionEntry.objects.filter(
            beneficiary=root,
            level=1,
            wallet_type=Wallet.WalletType.ROI,
        ).exclude(status=CommissionEntry.Status.VOIDED)
        self.assertEqual(entries.count(), 2)
        self.assertEqual(sum(e.amount for e in entries), Decimal("220.00"))
        self.assertNotEqual(sum(e.amount for e in entries), Decimal("110.00") * 48)

    def test_zero_required_directs_still_needs_matching_children(self):
        """Prod slabs with required_directs=0 must not unlock every ROI level."""
        PerformanceIncomeSlab.objects.update(required_directs=0)
        root = self._assoc("JOYMROOT00")
        mid = self._assoc("JOYMMID00Z", sponsor=root)
        buyer = self._assoc("JOYMBUY00Z", sponsor=mid, active=False)
        apply_investment_business(associate=buyer, amount=SALE, reference="INV-ZERO")
        self.assertEqual(CommissionEngine.unlocked_performance_levels(root), 1)
        self.assertFalse(
            CommissionEntry.objects.filter(
                beneficiary=root, source_associate=buyer, level=2, wallet_type=Wallet.WalletType.ROI
            ).exists()
        )

    def test_zero_required_directs_still_needs_n_children(self):
        """Blank/0 required_directs must not unlock every ROI depth."""
        from configuration.models import PerformanceIncomeSlab

        PerformanceIncomeSlab.objects.update(required_directs=0)
        root = self._assoc("JOYMROOT0D")
        mid = self._assoc("JOYMMID0D0", sponsor=root)
        buyer = self._assoc("JOYMBUY0D0", sponsor=mid, active=False)
        apply_investment_business(associate=buyer, amount=SALE, reference="INV-ZERO")
        self.assertEqual(CommissionEngine.unlocked_performance_levels(root), 1)
        self.assertFalse(
            CommissionEntry.objects.filter(
                beneficiary=root, source_associate=buyer, level=2, wallet_type=Wallet.WalletType.ROI
            ).exists()
        )

    def test_inactive_upline_does_not_receive_roi(self):
        root = self._assoc("JOYMINACT0", active=False)
        buyer = self._assoc("JOYMINACTB", sponsor=root, active=False)
        apply_investment_business(associate=buyer, amount=SALE, reference="INV-INACT")
        self.assertFalse(
            CommissionEntry.objects.filter(
                beneficiary=root, source_associate=buyer, wallet_type=Wallet.WalletType.ROI
            ).exists()
        )
        roi = Wallet.objects.get(associate=root, wallet_type=Wallet.WalletType.ROI)
        self.assertEqual(roi.balance, Decimal("0.00"))
