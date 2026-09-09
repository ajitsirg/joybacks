"""Wallet admin purge tests."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from associates.models import Associate
from wallets.models import LedgerEntry, Wallet
from wallets.purge import purge_wallet
from wallets.services import WalletService

User = get_user_model()


class WalletPurgeTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="wpurge", password="x", email="wp@t.test")
        self.assoc = Associate.objects.create(
            user=user,
            associate_id="JOYWPURGE01",
            referral_code="RWP01",
            mobile="9000000001",
            status=Associate.Status.INACTIVE,
        )
        WalletService.ensure_wallets(self.assoc)
        self.wallet = Wallet.objects.get(
            associate=self.assoc, wallet_type=Wallet.WalletType.ROI
        )
        WalletService.credit(
            associate=self.assoc,
            wallet_type=Wallet.WalletType.ROI,
            amount=Decimal("110.00"),
            reference="TEST-ROI",
            narration="test",
        )

    def test_soft_purge_removes_ledger_and_archives_wallet(self):
        self.assertEqual(LedgerEntry.objects.filter(wallet=self.wallet).count(), 1)
        result = purge_wallet(wallet=self.wallet, hard=False)
        self.assertEqual(result["ledger_removed"], 1)
        self.assertFalse(Wallet.objects.filter(pk=self.wallet.pk).exists())
        self.assertTrue(Wallet.all_objects.filter(pk=self.wallet.pk, is_deleted=True).exists())
        self.assertEqual(
            Wallet.all_objects.get(pk=self.wallet.pk).balance, Decimal("0.00")
        )
        self.assertEqual(LedgerEntry.all_objects.filter(wallet_id=self.wallet.pk).count(), 1)
        self.assertTrue(
            LedgerEntry.all_objects.filter(wallet_id=self.wallet.pk, is_deleted=True).exists()
        )

    def test_hard_purge_destroys_rows(self):
        pk = self.wallet.pk
        result = purge_wallet(wallet=self.wallet, hard=True)
        self.assertEqual(result["ledger_removed"], 1)
        self.assertFalse(Wallet.all_objects.filter(pk=pk).exists())
        self.assertFalse(LedgerEntry.all_objects.filter(wallet_id=pk).exists())
