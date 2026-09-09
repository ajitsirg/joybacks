"""Associate fund transfer: self (main → personal) and under-leg + commissions."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from associates.models import Associate
from commissions.constants import FARHOUSE_SALE_AMOUNT
from commissions.models import CommissionEntry
from configuration.models import LevelIncomePlan, LevelIncomeSlab
from genealogy.services import GenealogyService
from wallets.models import Wallet
from wallets.services import WalletService
from wallets.transfer import associate_fund_transfer

User = get_user_model()
SALE = FARHOUSE_SALE_AMOUNT


class AssociateFundTransferTests(TestCase):
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
        return User.objects.create_user(
            username=username, password="x", email=f"{username}@t.test"
        )

    def _assoc(self, code: str, *, sponsor: Associate | None = None, active: bool = True) -> Associate:
        user = self._user(code.lower())
        digits = "".join(ch for ch in code if ch.isdigit()) or "1"
        mobile = (digits * 4)[:10]
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
            can_fund_transfer=True,
        )
        if sponsor is None:
            GenealogyService.ensure_root(a)
        else:
            GenealogyService.attach_under_sponsor(a, sponsor, force=True)
        WalletService.ensure_wallets(a)
        return a

    def _main(self, assoc: Associate) -> Wallet:
        return Wallet.objects.get(associate=assoc, wallet_type=Wallet.WalletType.MAIN)

    def _personal(self, assoc: Associate) -> Wallet:
        return Wallet.objects.get(associate=assoc, wallet_type=Wallet.WalletType.PERSONAL)

    def test_self_transfer_is_rejected(self):
        root = self._assoc("JOYFTROOT01")
        member = self._assoc("JOYFTSELF01", sponsor=root, active=False)
        WalletService.credit(
            associate=member,
            wallet_type=Wallet.WalletType.MAIN,
            amount=SALE,
            reference="SEED-MAIN",
            narration="seed",
        )
        with self.assertRaises(ValueError):
            associate_fund_transfer(
                actor=member.user,
                to_associate_id=member.associate_id,
                amount=SALE,
                payment_method="upi",
            )
        self.assertEqual(self._main(member).balance, SALE)

    def test_under_leg_credits_recipient_main_and_commission(self):
        root = self._assoc("JOYFTROOT02")
        child = self._assoc("JOYFTCHILD2", sponsor=root, active=False)
        WalletService.credit(
            associate=root,
            wallet_type=Wallet.WalletType.MAIN,
            amount=SALE,
            reference="SEED-ROOT",
            narration="seed",
        )
        result = associate_fund_transfer(
            actor=root.user,
            to_associate_id=child.associate_id,
            amount=SALE,
            payment_method="neft",
        )
        self.assertFalse(result["self_topup"])
        self.assertEqual(self._main(root).balance, Decimal("0.00"))
        self.assertEqual(self._main(child).balance, SALE)
        child.refresh_from_db()
        self.assertGreaterEqual(child.personal_business, SALE)
        e = CommissionEntry.objects.get(
            beneficiary=root, level=1, wallet_type=Wallet.WalletType.INCOME
        )
        self.assertEqual(e.amount, Decimal("11000.00"))

    def test_rejects_amount_below_minimum_slab(self):
        root = self._assoc("JOYFTROOT03")
        WalletService.credit(
            associate=root,
            wallet_type=Wallet.WalletType.MAIN,
            amount=SALE,
            reference="SEED",
            narration="seed",
        )
        child = self._assoc("JOYFTCHILD3", sponsor=root, active=False)
        with self.assertRaises(ValueError):
            associate_fund_transfer(
                actor=root.user,
                to_associate_id=child.associate_id,
                amount=Decimal("100000.00"),
                payment_method="upi",
            )
