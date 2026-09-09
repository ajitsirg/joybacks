from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from associates.models import Associate
from configuration.models import WithdrawalSettings
from operations.models import DepositRequest, WithdrawalRequest
from operations.serializers import DepositSerializer
from operations.services import DepositService, WithdrawalService
from wallets.models import LedgerEntry, Wallet
from wallets.services import WalletService

User = get_user_model()


class FinancialRequestRegressionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        WithdrawalSettings.objects.create(
            name="Regression settings",
            min_amount=Decimal("100"),
            max_amount=Decimal("2000"),
            charge_percent=Decimal("10"),
            charge_flat=Decimal("0"),
            maker_checker_threshold=Decimal("500"),
            daily_limit=Decimal("700"),
        )
        self.associate = self._associate("FINREG01")
        self.reviewer = User.objects.create_user(
            email="reviewer@example.test", username="reviewer", password="x", is_staff=True
        )
        self.second_reviewer = User.objects.create_user(
            email="reviewer2@example.test", username="reviewer2", password="x", is_staff=True
        )

    def _associate(self, code):
        user = User.objects.create_user(
            email=f"{code.lower()}@example.test", username=code.lower(), password="x"
        )
        assoc = Associate.objects.create(
            user=user,
            associate_id=code,
            referral_code=f"R{code}",
            mobile="9" + code[-2:].zfill(2) + "1234567",
            status=Associate.Status.ACTIVE,
            kyc_verified=True,
        )
        WalletService.ensure_wallets(assoc)
        return assoc

    def _withdraw_wallet(self):
        return Wallet.objects.get(
            associate=self.associate, wallet_type=Wallet.WalletType.WITHDRAW
        )

    def test_deposit_validation_rejects_duplicate_references_and_repeat_approval(self):
        first = DepositRequest.objects.create(
            associate=self.associate,
            amount=Decimal("200"),
            wallet_type=Wallet.WalletType.MAIN,
            transaction_id="REF-001",
        )
        duplicate = DepositSerializer(
            data={"amount": "200", "wallet_type": "main", "transaction_id": "ref-001"}
        )
        self.assertFalse(duplicate.is_valid())
        self.assertIn("transaction_id", duplicate.errors)

        DepositService.approve(first, actor=self.reviewer)
        with self.assertRaisesMessage(ValueError, "not pending"):
            DepositService.approve(first, actor=self.reviewer)

        wallet = Wallet.objects.get(associate=self.associate, wallet_type=Wallet.WalletType.MAIN)
        self.assertEqual(wallet.balance, Decimal("200"))
        self.assertEqual(
            LedgerEntry.objects.filter(wallet=wallet, entry_type=LedgerEntry.EntryType.CREDIT).count(),
            1,
        )

    def test_deposit_endpoints_are_immutable_after_submission(self):
        request = DepositRequest.objects.create(
            associate=self.associate,
            amount=Decimal("200"),
            wallet_type=Wallet.WalletType.MAIN,
            transaction_id="IMMUTABLE-001",
        )
        self.client.force_authenticate(self.associate.user)
        response = self.client.patch(
            f"/api/v1/ops/deposits/{request.id}/",
            {"amount": "1"},
            format="json",
        )
        self.assertEqual(response.status_code, 405)

    def test_withdrawal_hold_is_refunded_only_once(self):
        WalletService.credit(
            associate=self.associate,
            wallet_type=Wallet.WalletType.WITHDRAW,
            amount=Decimal("400"),
            reference="SEED-WD",
        )
        withdrawal = WithdrawalService.create(
            associate=self.associate, amount=Decimal("400"), bank_detail="Bank account 1234"
        )
        self.assertEqual(withdrawal.net_amount, Decimal("360.00"))
        self.assertIsNotNone(withdrawal.hold_ledger_entry_id)
        self.assertEqual(self._withdraw_wallet().balance, Decimal("0"))

        WithdrawalService.reject(withdrawal, actor=self.reviewer, reason="Rejected")
        self.assertEqual(self._withdraw_wallet().balance, Decimal("400"))
        with self.assertRaisesMessage(ValueError, "not pending or verified"):
            WithdrawalService.reject(withdrawal, actor=self.reviewer, reason="Again")
        self.assertEqual(self._withdraw_wallet().balance, Decimal("400"))

    def test_withdrawal_enforces_kyc_pending_and_daily_limits(self):
        self.associate.kyc_verified = False
        self.associate.save(update_fields=["kyc_verified", "updated_at"])
        with self.assertRaisesMessage(ValueError, "KYC"):
            WithdrawalService.create(
                associate=self.associate, amount=Decimal("400"), bank_detail="Bank account 1234"
            )

        self.associate.kyc_verified = True
        self.associate.save(update_fields=["kyc_verified", "updated_at"])
        WalletService.credit(
            associate=self.associate,
            wallet_type=Wallet.WalletType.WITHDRAW,
            amount=Decimal("1000"),
            reference="SEED-LIMIT",
        )
        first = WithdrawalService.create(
            associate=self.associate, amount=Decimal("400"), bank_detail="Bank account 1234"
        )
        with self.assertRaisesMessage(ValueError, "pending withdrawal"):
            WithdrawalService.create(
                associate=self.associate, amount=Decimal("100"), bank_detail="Bank account 1234"
            )
        WithdrawalService.approve(first, actor=self.reviewer)
        with self.assertRaisesMessage(ValueError, "Daily withdrawal limit"):
            WithdrawalService.create(
                associate=self.associate, amount=Decimal("400"), bank_detail="Bank account 1234"
            )

    def test_high_value_withdrawal_requires_two_reviewers(self):
        WalletService.credit(
            associate=self.associate,
            wallet_type=Wallet.WalletType.WITHDRAW,
            amount=Decimal("600"),
            reference="SEED-MAKER-CHECKER",
        )
        withdrawal = WithdrawalService.create(
            associate=self.associate, amount=Decimal("600"), bank_detail="Bank account 1234"
        )
        self.assertTrue(withdrawal.requires_maker_checker)
        WithdrawalService.verify(withdrawal, actor=self.reviewer)
        with self.assertRaisesMessage(ValueError, "different authorized"):
            WithdrawalService.approve(withdrawal, actor=self.reviewer)
        WithdrawalService.approve(withdrawal, actor=self.second_reviewer)
        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, WithdrawalRequest.Status.COMPLETED)
