from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from associates.models import Associate
from associates.services import AssociateService
from audit.services import write_audit
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
        cfg = ConfigRepository.withdrawal()
        if amount < cfg.min_amount or amount > cfg.max_amount:
            raise ValueError(f"Amount must be between {cfg.min_amount} and {cfg.max_amount}")
        charge = (amount * cfg.charge_percent / Decimal("100")) + cfg.charge_flat
        charge = charge.quantize(Decimal("0.01"))
        net = (amount - charge).quantize(Decimal("0.01"))
        maker = amount >= cfg.maker_checker_threshold
        return charge, net, maker

    @staticmethod
    @transaction.atomic
    def create(*, associate: Associate, amount: Decimal, bank_detail: str = "") -> WithdrawalRequest:
        charge, net, maker = WithdrawalService.compute_charges(amount)
        WalletService.debit(
            associate=associate,
            wallet_type=Wallet.WalletType.WITHDRAW,
            amount=amount,
            reference="WD-HOLD",
            narration="Withdrawal request",
        )
        return WithdrawalRequest.objects.create(
            associate=associate,
            amount=amount,
            charge_amount=charge,
            net_amount=net,
            bank_detail=bank_detail,
            requires_maker_checker=maker,
            status=WithdrawalRequest.Status.PENDING,
        )

    @staticmethod
    @transaction.atomic
    def approve(withdrawal: WithdrawalRequest, *, actor) -> WithdrawalRequest:
        if withdrawal.status != WithdrawalRequest.Status.PENDING:
            raise ValueError("Withdrawal is not pending")
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
        if withdrawal.status != WithdrawalRequest.Status.PENDING:
            raise ValueError("Withdrawal is not pending")
        WalletService.credit(
            associate=withdrawal.associate,
            wallet_type=Wallet.WalletType.WITHDRAW,
            amount=withdrawal.amount,
            reference=f"WD-REFUND-{withdrawal.id}",
            narration="Withdrawal rejected — refund",
        )
        withdrawal.status = WithdrawalRequest.Status.REJECTED
        withdrawal.reviewed_by = actor
        withdrawal.reviewed_at = timezone.now()
        withdrawal.rejection_reason = reason
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
