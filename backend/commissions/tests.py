"""Level-based farmhouse commission: unlock by directs + configured %."""

from decimal import Decimal
from hashlib import md5

from django.contrib.auth import get_user_model
from django.test import TestCase

from associates.models import Associate
from commissions.constants import FARHOUSE_SALE_AMOUNT
from commissions.models import CommissionEntry
from commissions.services import CommissionEngine
from configuration.models import LevelIncomePlan, LevelIncomeSlab
from genealogy.services import GenealogyService
from wallets.business import apply_investment_business
from wallets.models import Wallet
from wallets.services import WalletService

User = get_user_model()
SALE = FARHOUSE_SALE_AMOUNT


class LevelCommissionTests(TestCase):
    def setUp(self):
        plan, _ = LevelIncomePlan.objects.get_or_create(
            code="direct-level",
            defaults={"name": "Direct Level Income", "max_levels": 5, "is_active": True},
        )
        plan.max_levels = 5
        plan.is_active = True
        plan.save()
        for level, pct in [
            (1, "5.0000"),
            (2, "2.5000"),
            (3, "2.0000"),
            (4, "1.0000"),
            (5, "0.5000"),
        ]:
            LevelIncomeSlab.objects.update_or_create(
                plan=plan,
                level=level,
                defaults={"percent": Decimal(pct), "is_active": True},
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

    def test_one_direct_sale_pays_level1_only(self):
        root = self._assoc("JOYROOT001")
        buyer = self._assoc("JOYBUY0001", sponsor=root, active=False)

        apply_investment_business(associate=buyer, amount=SALE, reference="SALE-1")

        entries = CommissionEntry.objects.filter(beneficiary=root, reference="SALE-1")
        self.assertEqual(entries.count(), 1)
        e = entries.get()
        self.assertEqual(e.level, 1)
        self.assertEqual(e.percent, Decimal("5.0000"))
        self.assertEqual(e.sale_amount, SALE)
        self.assertEqual(e.amount, Decimal("11000.00"))
        self.assertEqual(e.status, CommissionEntry.Status.CREDITED)
        self.assertEqual(CommissionEngine.unlocked_commission_levels(root), 1)

    def test_two_directs_unlock_level2_on_deeper_sale(self):
        root = self._assoc("JOYROOT002")
        d1 = self._assoc("JOYD100002", sponsor=root)  # already Active = 1 unit
        d2 = self._assoc("JOYD200002", sponsor=root, active=False)
        # Complete 2nd direct sale → unlock L1+L2
        apply_investment_business(associate=d2, amount=SALE, reference="SALE-D2")
        self.assertEqual(CommissionEngine.unlocked_commission_levels(root), 2)

        # Level-2 buyer under d1
        l2 = self._assoc("JOYL200002", sponsor=d1, active=False)
        apply_investment_business(associate=l2, amount=SALE, reference="SALE-L2")

        e = CommissionEntry.objects.get(beneficiary=root, reference="SALE-L2", level=2)
        self.assertEqual(e.percent, Decimal("2.5000"))
        self.assertEqual(e.amount, Decimal("5500.00"))
        # d1 also earns L1 on this sale
        e1 = CommissionEntry.objects.get(beneficiary=d1, reference="SALE-L2", level=1)
        self.assertEqual(e1.amount, Decimal("11000.00"))

    def test_locked_levels_not_paid(self):
        root = self._assoc("JOYROOT003")
        d1 = self._assoc("JOYD100003", sponsor=root)  # only 1 direct → L1 only
        l2 = self._assoc("JOYL200003", sponsor=d1, active=False)
        apply_investment_business(associate=l2, amount=SALE, reference="SALE-LOCK")

        self.assertFalse(
            CommissionEntry.objects.filter(beneficiary=root, reference="SALE-LOCK", level=2).exists()
        )
        # d1 has 1 direct sale → gets L1
        self.assertTrue(
            CommissionEntry.objects.filter(beneficiary=d1, reference="SALE-LOCK", level=1).exists()
        )

    def test_duplicate_reference_not_double_paid(self):
        root = self._assoc("JOYROOT004")
        buyer = self._assoc("JOYBUY0004", sponsor=root, active=False)
        apply_investment_business(associate=buyer, amount=SALE, reference="SALE-DUP")
        # Second distribute with same reference must not credit again
        CommissionEngine.distribute_level_income(
            source_associate=buyer,
            amount=SALE,
            reference="SALE-DUP",
        )
        self.assertEqual(
            CommissionEntry.objects.filter(beneficiary=root, reference="SALE-DUP", level=1).count(),
            1,
        )

    def test_sub_farmhouse_amount_skips_commission(self):
        root = self._assoc("JOYROOT005")
        buyer = self._assoc("JOYBUY0005", sponsor=root, active=False)
        apply_investment_business(associate=buyer, amount=Decimal("100000"), reference="SALE-SMALL")
        self.assertEqual(CommissionEntry.objects.filter(reference="SALE-SMALL").count(), 0)

    def test_inactive_sponsor_does_not_earn_level_income(self):
        root = self._assoc("JOYROOT006", active=False)
        buyer = self._assoc("JOYBUY0006", sponsor=root, active=False)
        apply_investment_business(associate=buyer, amount=SALE, reference="SALE-INACT")
        self.assertFalse(
            CommissionEntry.objects.filter(beneficiary=root, reference="SALE-INACT").exists()
        )
        w = Wallet.objects.get(associate=root, wallet_type=Wallet.WalletType.INCOME)
        self.assertEqual(w.balance, Decimal("0.00"))

    def test_missing_plan_still_pays_official_level1(self):
        LevelIncomePlan.objects.all().delete()
        root = self._assoc("JOYROOT007")
        buyer = self._assoc("JOYBUY0007", sponsor=root, active=False)
        apply_investment_business(associate=buyer, amount=SALE, reference="SALE-NOPLAN")
        e = CommissionEntry.objects.get(beneficiary=root, reference="SALE-NOPLAN", level=1)
        self.assertEqual(e.amount, Decimal("11000.00"))
        self.assertEqual(e.percent, Decimal("5.0000"))

    def test_five_direct_sales_level1_total_55000(self):
        """5 × ₹2,20,000 at Level 1 × 5% = ₹55,000 (from actual buyers, not a hardcoded headcount)."""
        root = self._assoc("JOYROOT5D0")
        for i in range(1, 6):
            buyer = self._assoc(f"JOY5D{i:03d}", sponsor=root, active=False)
            apply_investment_business(associate=buyer, amount=SALE, reference=f"SALE-5D{i}")
        entries = CommissionEntry.objects.filter(
            beneficiary=root, level=1, wallet_type=Wallet.WalletType.INCOME
        ).exclude(status=CommissionEntry.Status.VOIDED)
        self.assertEqual(entries.count(), 5)
        self.assertEqual(sum(e.amount for e in entries), Decimal("55000.00"))
        self.assertEqual(CommissionEngine.unlocked_commission_levels(root), 5)

    def test_level_counts_come_from_genealogy_not_example_tree(self):
        """2 directs + 2 L2 buyers → L1 ₹22,000 and L2 ₹11,000. Do not use 5/10/20/40/80."""
        root = self._assoc("JOYROOTGEO")
        d1 = self._assoc("JOYGEOD001", sponsor=root, active=False)
        d2 = self._assoc("JOYGEOD002", sponsor=root, active=False)
        apply_investment_business(associate=d1, amount=SALE, reference="SALE-GEO-D1")
        apply_investment_business(associate=d2, amount=SALE, reference="SALE-GEO-D2")
        self.assertEqual(CommissionEngine.unlocked_commission_levels(root), 2)

        l2a = self._assoc("JOYGEOL2A", sponsor=d1, active=False)
        l2b = self._assoc("JOYGEOL2B", sponsor=d2, active=False)
        apply_investment_business(associate=l2a, amount=SALE, reference="SALE-GEO-L2A")
        apply_investment_business(associate=l2b, amount=SALE, reference="SALE-GEO-L2B")

        l1 = CommissionEntry.objects.filter(beneficiary=root, level=1, wallet_type=Wallet.WalletType.INCOME)
        l2 = CommissionEntry.objects.filter(beneficiary=root, level=2, wallet_type=Wallet.WalletType.INCOME)
        self.assertEqual(sum(e.amount for e in l1), Decimal("22000.00"))
        self.assertEqual(sum(e.amount for e in l2), Decimal("11000.00"))
        self.assertNotEqual(sum(e.amount for e in l1), Decimal("55000.00"))

    def test_users_unlock_independently(self):
        """A unlocked to L3 does not grant B extra levels. B with 1 direct earns L1 only."""
        a = self._assoc("JOYINDA000")
        b = self._assoc("JOYINDB000", sponsor=a, active=False)
        apply_investment_business(associate=b, amount=SALE, reference="SALE-IND-B")
        for i in range(2, 4):
            extra = self._assoc(f"JOYINDA{i:03d}", sponsor=a, active=False)
            apply_investment_business(associate=extra, amount=SALE, reference=f"SALE-IND-A{i}")
        self.assertEqual(CommissionEngine.unlocked_commission_levels(a), 3)
        self.assertEqual(CommissionEngine.unlocked_commission_levels(b), 0)

        c = self._assoc("JOYINDC000", sponsor=b, active=False)
        apply_investment_business(associate=c, amount=SALE, reference="SALE-IND-C")
        self.assertEqual(CommissionEngine.unlocked_commission_levels(b), 1)
        self.assertEqual(
            CommissionEntry.objects.get(beneficiary=b, reference="SALE-IND-C", level=1).amount,
            Decimal("11000.00"),
        )
        self.assertEqual(
            CommissionEntry.objects.get(beneficiary=a, reference="SALE-IND-C", level=2).amount,
            Decimal("5500.00"),
        )
        self.assertFalse(
            CommissionEntry.objects.filter(beneficiary=b, reference="SALE-IND-C", level=2).exists()
        )

        d = self._assoc("JOYINDD000", sponsor=c, active=False)
        apply_investment_business(associate=d, amount=SALE, reference="SALE-IND-D")
        self.assertEqual(
            CommissionEntry.objects.get(beneficiary=a, reference="SALE-IND-D", level=3).amount,
            Decimal("4400.00"),
        )
        self.assertFalse(
            CommissionEntry.objects.filter(beneficiary=b, reference="SALE-IND-D", level=2).exists()
        )

    def test_third_direct_sale_unlocks_level3_for_later_sales(self):
        root = self._assoc("JOYROOTUL3")
        d1 = self._assoc("JOYUL3D001", sponsor=root)
        mid = self._assoc("JOYUL3MID0", sponsor=d1)
        deep = self._assoc("JOYUL3DEEP", sponsor=mid, active=False)
        apply_investment_business(associate=deep, amount=SALE, reference="SALE-UL3-EARLY")
        self.assertFalse(
            CommissionEntry.objects.filter(beneficiary=root, reference="SALE-UL3-EARLY", level=3).exists()
        )

        d2 = self._assoc("JOYUL3D002", sponsor=root, active=False)
        d3 = self._assoc("JOYUL3D003", sponsor=root, active=False)
        apply_investment_business(associate=d2, amount=SALE, reference="SALE-UL3-D2")
        apply_investment_business(associate=d3, amount=SALE, reference="SALE-UL3-D3")
        self.assertEqual(CommissionEngine.unlocked_commission_levels(root), 3)

        later = self._assoc("JOYUL3LATR", sponsor=mid, active=False)
        apply_investment_business(associate=later, amount=SALE, reference="SALE-UL3-LATE")
        e = CommissionEntry.objects.get(beneficiary=root, reference="SALE-UL3-LATE", level=3)
        self.assertEqual(e.amount, Decimal("4400.00"))
        self.assertEqual(e.percent, Decimal("2.0000"))

    def test_one_child_with_five_units_unlocks_only_level1(self):
        """Units on one immediate member do not unlock extra sale levels."""
        root = self._assoc("JOYROOT1U5")
        buyer = self._assoc("JOYBUY1U05", sponsor=root, active=False)
        apply_investment_business(associate=buyer, amount=SALE * 5, reference="SALE-5U")
        self.assertEqual(CommissionEngine.unlocked_commission_levels(root), 1)
        self.assertEqual(
            CommissionEntry.objects.filter(beneficiary=root, reference="SALE-5U").count(),
            1,
        )
        self.assertEqual(
            CommissionEntry.objects.get(beneficiary=root, reference="SALE-5U", level=1).amount,
            Decimal("55000.00"),
        )
        self.assertFalse(
            CommissionEntry.objects.filter(beneficiary=root, reference="SALE-5U", level=2).exists()
        )
