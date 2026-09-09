from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from associates.models import Associate
from associates.services import AssociateService
from audit.services import write_audit
from configuration.models import ActivationRule
from configuration.repository import ConfigRepository
from operations.models import DepositRequest, KYCSubmission, WithdrawalRequest
from wallets.business import apply_investment_business
from wallets.models import Wallet
from wallets.services import WalletService


class KYCService:
    @staticmethod
    @transaction.atomic
    def approve(submission: KYCSubmission, *, actor) -> KYCSubmission:
        if submission.status == KYCSubmission.Status.APPROVED and getattr(
            submission.associate, "kyc_verified", False
        ):
            return submission
        if submission.status == KYCSubmission.Status.REJECTED:
            raise ValueError("KYC is rejected — ask the associate to re-submit, then approve")

        try:
            assoc = Associate.objects.select_for_update().get(pk=submission.associate_id)
        except Associate.DoesNotExist as exc:
            raise ValueError("Associate is deleted — cannot approve KYC") from exc
        # Staff/leader KYC approve completes the join if still pending
        if assoc.status == Associate.Status.PENDING:
            AssociateService.leader_approve(assoc, actor=actor)
            submission.refresh_from_db()
            return submission
        submission.status = KYCSubmission.Status.APPROVED
        submission.reviewed_by = actor
        submission.reviewed_at = timezone.now()
        submission.rejection_reason = ""
        submission.save(
            update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason", "updated_at"]
        )
        assoc.kyc_verified = True
        assoc.save(update_fields=["kyc_verified", "updated_at"])
        write_audit(
            actor=actor,
            action="kyc.approve",
            module="kyc",
            object_type="KYCSubmission",
            object_id=str(submission.id),
        )
        return submission

    @staticmethod
    @transaction.atomic
    def reject(submission: KYCSubmission, *, actor, reason: str) -> KYCSubmission:
        if submission.status == KYCSubmission.Status.REJECTED and not getattr(
            submission.associate, "kyc_verified", False
        ):
            return submission

        try:
            assoc = Associate.objects.select_for_update().get(pk=submission.associate_id)
        except Associate.DoesNotExist as exc:
            raise ValueError("Associate is deleted — cannot reject KYC") from exc
        if assoc.status == Associate.Status.PENDING:
            AssociateService.leader_reject(assoc, actor=actor, reason=reason)
            submission.refresh_from_db()
            return submission
        submission.status = KYCSubmission.Status.REJECTED
        submission.reviewed_by = actor
        submission.reviewed_at = timezone.now()
        submission.rejection_reason = reason or "Rejected by admin"
        submission.save(
            update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason", "updated_at"]
        )
        assoc.kyc_verified = False
        assoc.save(update_fields=["kyc_verified", "updated_at"])
        write_audit(
            actor=actor,
            action="kyc.reject",
            module="kyc",
            object_type="KYCSubmission",
            object_id=str(submission.id),
            metadata={"reason": reason},
        )
        return submission


class DepositService:
    @staticmethod
    @transaction.atomic
    def approve(deposit: DepositRequest, *, actor) -> DepositRequest:
        deposit = DepositRequest.objects.select_for_update().get(pk=deposit.pk)
        if deposit.status != DepositRequest.Status.PENDING:
            raise ValueError("Deposit is not pending")
        assoc = Associate.objects.select_for_update().get(pk=deposit.associate_id)
        if assoc.status in {
            Associate.Status.PENDING,
            Associate.Status.REJECTED,
            Associate.Status.BLOCKED,
        }:
            raise ValueError(
                "Associate must be approved (Inactive/Active) before deposits can be completed"
            )
        if deposit.amount <= 0:
            raise ValueError("Deposit amount must be positive")
        if deposit.wallet_type not in {Wallet.WalletType.MAIN, Wallet.WalletType.PERSONAL}:
            raise ValueError("Deposits are allowed only to main or personal wallets")
        reference = " ".join((deposit.transaction_id or "").strip().split())
        if not reference:
            raise ValueError("Payment reference is required")
        if DepositRequest.objects.exclude(pk=deposit.pk).filter(transaction_id__iexact=reference).exists():
            raise ValueError("This payment reference has already been submitted")
        activation_rule = ActivationRule.objects.filter(is_active=True).order_by("created_at").first()
        if activation_rule and deposit.amount < activation_rule.min_deposit:
            raise ValueError(
                f"Deposit must be at least {activation_rule.min_deposit} under the active activation rule"
            )

        deposit.status = DepositRequest.Status.COMPLETED
        deposit.reviewed_by = actor
        deposit.reviewed_at = timezone.now()
        deposit.applied_at = timezone.now()
        deposit.save()

        WalletService.credit(
            associate=deposit.associate,
            wallet_type=deposit.wallet_type or Wallet.WalletType.MAIN,
            amount=deposit.amount,
            reference=deposit.transaction_id or str(deposit.id),
            narration="Deposit approved",
        )

        apply_investment_business(
            associate=assoc,
            amount=deposit.amount,
            reference=f"DEP-{deposit.id}",
        )
        write_audit(
            actor=actor,
            action="deposit.approve",
            module="deposits",
            object_type="DepositRequest",
            object_id=str(deposit.id),
            metadata={"amount": str(deposit.amount)},
        )
        return deposit

    @staticmethod
    @transaction.atomic
    def reject(deposit: DepositRequest, *, actor, reason: str) -> DepositRequest:
        deposit = DepositRequest.objects.select_for_update().get(pk=deposit.pk)
        if deposit.status != DepositRequest.Status.PENDING:
            raise ValueError("Deposit is not pending")
        deposit.status = DepositRequest.Status.REJECTED
        deposit.reviewed_by = actor
        deposit.reviewed_at = timezone.now()
        deposit.rejection_reason = reason
        deposit.save()
        write_audit(
            actor=actor,
            action="deposit.reject",
            module="deposits",
            object_type="DepositRequest",
            object_id=str(deposit.id),
            metadata={"reason": reason},
        )
        return deposit


class WithdrawalService:
    @staticmethod
    def compute_charges(amount: Decimal) -> tuple[Decimal, Decimal, bool]:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        cfg = ConfigRepository.withdrawal()
        if amount < cfg.min_amount or amount > cfg.max_amount:
            raise ValueError(f"Amount must be between {cfg.min_amount} and {cfg.max_amount}")
        charge = (amount * cfg.charge_percent / Decimal("100")) + cfg.charge_flat
        charge = charge.quantize(Decimal("0.01"))
        net = (amount - charge).quantize(Decimal("0.01"))
        if net <= 0:
            raise ValueError("Withdrawal charges leave no payable amount")
        maker = amount >= cfg.maker_checker_threshold
        return charge, net, maker

    @staticmethod
    @transaction.atomic
    def create(*, associate: Associate, amount: Decimal, bank_detail: str = "") -> WithdrawalRequest:
        try:
            amount = Decimal(amount).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("Amount must be a valid monetary value") from exc
        bank_detail = " ".join((bank_detail or "").strip().split())
        if not bank_detail:
            raise ValueError("Bank details are required")
        associate = Associate.objects.select_for_update().get(pk=associate.pk)
        if associate.is_deleted or associate.status != Associate.Status.ACTIVE:
            raise ValueError("Only active associates can request withdrawals")
        if not associate.kyc_verified:
            raise ValueError("KYC verification is required before requesting a withdrawal")
        charge, net, maker = WithdrawalService.compute_charges(amount)
        cfg = ConfigRepository.withdrawal()
        today = timezone.localdate()
        daily_total = (
            WithdrawalRequest.objects.filter(
                associate=associate,
                created_at__date=today,
            )
            .exclude(status=WithdrawalRequest.Status.REJECTED)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0")
        )
        if cfg.daily_limit > 0 and daily_total + amount > cfg.daily_limit:
            raise ValueError(f"Daily withdrawal limit of {cfg.daily_limit} would be exceeded")
        if WithdrawalRequest.objects.filter(
            associate=associate,
            status__in=[WithdrawalRequest.Status.PENDING, WithdrawalRequest.Status.VERIFIED],
        ).exists():
            raise ValueError("You already have a pending withdrawal request")
        WalletService.ensure_wallets(associate)
        withdrawal = WithdrawalRequest.objects.create(
            associate=associate,
            amount=amount,
            charge_amount=charge,
            net_amount=net,
            bank_detail=bank_detail,
            requires_maker_checker=maker,
            status=WithdrawalRequest.Status.PENDING,
        )
        hold = WalletService.debit(
            associate=associate,
            wallet_type=Wallet.WalletType.WITHDRAW,
            amount=amount,
            reference=f"WD-HOLD-{withdrawal.id}",
            narration="Withdrawal request",
            meta={"withdrawal_id": str(withdrawal.id)},
        )
        withdrawal.hold_ledger_entry = hold
        withdrawal.save(update_fields=["hold_ledger_entry", "updated_at"])
        return withdrawal

    @staticmethod
    @transaction.atomic
    def verify(withdrawal: WithdrawalRequest, *, actor) -> WithdrawalRequest:
        withdrawal = WithdrawalRequest.objects.select_for_update().get(pk=withdrawal.pk)
        if withdrawal.status != WithdrawalRequest.Status.PENDING:
            raise ValueError("Withdrawal is not pending")
        if not withdrawal.requires_maker_checker:
            raise ValueError("This withdrawal does not require verification; complete it directly")
        withdrawal.status = WithdrawalRequest.Status.VERIFIED
        withdrawal.verified_by = actor
        withdrawal.verified_at = timezone.now()
        withdrawal.save(update_fields=["status", "verified_by", "verified_at", "updated_at"])
        write_audit(
            actor=actor,
            action="withdrawal.verify",
            module="withdrawals",
            object_type="WithdrawalRequest",
            object_id=str(withdrawal.id),
        )
        return withdrawal

    @staticmethod
    @transaction.atomic
    def approve(withdrawal: WithdrawalRequest, *, actor) -> WithdrawalRequest:
        withdrawal = WithdrawalRequest.objects.select_for_update().get(pk=withdrawal.pk)
        expected_state = (
            WithdrawalRequest.Status.VERIFIED
            if withdrawal.requires_maker_checker
            else WithdrawalRequest.Status.PENDING
        )
        if withdrawal.status != expected_state:
            action = "verified before completion" if withdrawal.requires_maker_checker else "pending"
            raise ValueError(f"Withdrawal must be {action}")
        if withdrawal.requires_maker_checker and withdrawal.verified_by_id == actor.id:
            raise ValueError("A different authorized staff member must complete this withdrawal")
        withdrawal.status = WithdrawalRequest.Status.COMPLETED
        withdrawal.reviewed_by = actor
        withdrawal.reviewed_at = timezone.now()
        withdrawal.transferred_at = timezone.now()
        withdrawal.save()
        write_audit(
            actor=actor,
            action="withdrawal.approve",
            module="withdrawals",
            object_type="WithdrawalRequest",
            object_id=str(withdrawal.id),
        )
        return withdrawal

    @staticmethod
    @transaction.atomic
    def reject(withdrawal: WithdrawalRequest, *, actor, reason: str) -> WithdrawalRequest:
        withdrawal = WithdrawalRequest.objects.select_for_update().get(pk=withdrawal.pk)
        if withdrawal.status not in {
            WithdrawalRequest.Status.PENDING,
            WithdrawalRequest.Status.VERIFIED,
        }:
            raise ValueError("Withdrawal is not pending or verified")
        associate = Associate.objects.select_for_update().get(pk=withdrawal.associate_id)
        if withdrawal.refund_ledger_entry_id:
            raise ValueError("Withdrawal has already been refunded")
        refund = WalletService.credit(
            associate=associate,
            wallet_type=Wallet.WalletType.WITHDRAW,
            amount=withdrawal.amount,
            reference=f"WD-REFUND-{withdrawal.id}",
            narration="Withdrawal rejected — refund",
            meta={"withdrawal_id": str(withdrawal.id)},
        )
        withdrawal.status = WithdrawalRequest.Status.REJECTED
        withdrawal.reviewed_by = actor
        withdrawal.reviewed_at = timezone.now()
        withdrawal.rejection_reason = reason
        withdrawal.refund_ledger_entry = refund
        withdrawal.save()
        write_audit(
            actor=actor,
            action="withdrawal.reject",
            module="withdrawals",
            object_type="WithdrawalRequest",
            object_id=str(withdrawal.id),
            metadata={"reason": reason},
        )
        return withdrawal
