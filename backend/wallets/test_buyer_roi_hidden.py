"""Investor own monthly ROI ₹2,200 must not appear as a paid amount."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from associates.models import Associate
from genealogy.services import GenealogyService
from wallets.models import LedgerEntry, Wallet
from wallets.services import WalletService
from wallets.visibility import exclude_buyer_self_roi, visible_wallet_balance

User = get_user_model()


class BuyerSelfRoiHiddenTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="joybuyer", password="x", email="joybuyer@t.test")
        self.assoc = Associate.objects.create(
            user=user,
            associate_id="JOYBUY2200",
            referral_code="RBUY2200",
            mobile="9000002200",
            status=Associate.Status.ACTIVE,
        )
        GenealogyService.ensure_root(self.assoc)
        WalletService.ensure_wallets(self.assoc)
        WalletService.credit(
            associate=self.assoc,
            wallet_type=Wallet.WalletType.ROI,
            amount=Decimal("2200.00"),
            reference="MRI-11db28bf-9bc2-46d5-a8c3-360a8d2bfa99-M1",
            narration="Monthly ROI M1",
        )
        WalletService.credit(
            associate=self.assoc,
            wallet_type=Wallet.WalletType.ROI,
            amount=Decimal("110.00"),
            reference="MRI-11db28bf-9bc2-46d5-a8c3-360a8d2bfa99-M1-L1",
            narration="Level 1 ROI Income — 5% of base ROI ₹2200.00 = ₹110.00",
        )

    def test_ledger_hides_buyer_self_credit(self):
        roi = Wallet.objects.get(associate=self.assoc, wallet_type=Wallet.WalletType.ROI)
        qs = LedgerEntry.objects.filter(wallet=roi)
        self.assertEqual(qs.count(), 2)
        visible = exclude_buyer_self_roi(qs)
        self.assertEqual(visible.count(), 1)
        row = visible.get()
        self.assertEqual(row.amount, Decimal("110.00"))
        self.assertTrue(row.reference.endswith("-L1"))

    def test_visible_roi_balance_excludes_2200(self):
        roi = Wallet.objects.get(associate=self.assoc, wallet_type=Wallet.WalletType.ROI)
        self.assertEqual(roi.balance, Decimal("2310.00"))
        self.assertEqual(visible_wallet_balance(roi), Decimal("110.00"))
