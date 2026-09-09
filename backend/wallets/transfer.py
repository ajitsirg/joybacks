"""Admin mint credit and associate fixed-amount fund transfer / top-up."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from associates.models import Associate
from audit.services import write_audit
from wallets.business import apply_investment_business
from wallets.fund_packages import (
    format_lakh,
    is_fixed_fund_amount,
    normalize_payment_method,
    payment_method_label,
)
from wallets.models import FundTransferRequest, LedgerEntry, Wallet
from wallets.services import WalletService

_PROOF_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".pdf", ".heic"}
_PROOF_MAX_BYTES = 8 * 1024 * 1024


def _normalize_utr(raw: str) -> str:
    utr = " ".join(str(raw or "").strip().split())
    if not utr:
        raise ValueError("Enter the UTR / transaction ID")
    if len(utr) < 4 or len(utr) > 64:
        raise ValueError("UTR / transaction ID must be 4–64 characters")
    return utr


def _validate_proof(proof) -> None:
    if proof is None:
        raise ValueError("Upload a payment screenshot, receipt, or PDF")
    name = str(getattr(proof, "name", "") or "").lower()
    suffix = name[name.rfind(".") :] if "." in name else ""
    if suffix not in _PROOF_SUFFIXES:
        raise ValueError("Proof must be an image (JPG, PNG, WEBP) or PDF")
    size = getattr(proof, "size", 0) or 0
    if size > _PROOF_MAX_BYTES:
        raise ValueError("Proof file must be 8 MB or smaller")


def _recipient_in_leg(*, actor_associate: Associate, recipient: Associate) -> bool:
    """True if recipient is a genealogy descendant of actor (never self)."""
    if recipient.pk == actor_associate.pk:
        return False
    from genealogy.models import GenealogyClosure

    return GenealogyClosure.objects.filter(
        ancestor=actor_associate,
        descendant=recipient,
        depth__gt=0,
    ).exists()


@transaction.atomic
def admin_fund_transfer(
    *,
    actor,
    to_associate_id: str,
    wallet_type: str,
    amount: Decimal,
    narration: str = "Admin fund transfer",
    apply_business: bool = False,
    payment_method: str = "",
    from_associate_id: str = "",
    company_mint: bool = False,
) -> LedgerEntry:
    """Staff transfer: debit sender (or company mint) and credit recipient."""
    associate = Associate.objects.get(associate_id__iexact=to_associate_id)
    WalletService.ensure_wallets(associate)
    if wallet_type not in {c.value for c in Wallet.WalletType}:
        raise ValueError("Invalid wallet type")
    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    if amount <= 0:
        raise ValueError("Amount must be positive")

    pay_code = normalize_payment_method(payment_method)
    pay_label = payment_method_label(pay_code)
    source_id = (from_associate_id or "").strip()
    mint = bool(company_mint)
    if not mint and not source_id:
        raise ValueError("Select the associate to debit, or enable company mint")
    if not mint:
        source = Associate.objects.select_for_update().get(associate_id__iexact=source_id)
        if source.pk == associate.pk:
            raise ValueError("From and to associate must be different")
        WalletService.ensure_wallets(source)
        try:
            WalletService.debit(
                associate=source,
                wallet_type=wallet_type,
                amount=amount,
                reference=f"ADMIN-{actor.id}",
                narration=f"Admin transfer to {associate.associate_id}: {narration}",
                meta={
                    "by": actor.email,
                    "to": associate.associate_id,
                    "payment_method": pay_code,
                },
            )
        except ValueError as exc:
            if "Insufficient" in str(exc):
                raise ValueError("Not enough balance") from exc
            raise

    entry = WalletService.credit(
        associate=associate,
        wallet_type=wallet_type,
        amount=amount,
        reference=f"ADMIN-{actor.id}",
        narration=narration,
        meta={
            "by": actor.email,
            "apply_business": apply_business,
            "payment_method": pay_code,
            "payment_method_label": pay_label,
            "from": source_id or None,
            "company_mint": mint,
        },
    )

    if apply_business:
        if wallet_type != Wallet.WalletType.MAIN:
            raise ValueError("Business calculation applies only to main (fund) wallet")
        if not is_fixed_fund_amount(amount):
            raise ValueError("Business calculation requires a fixed fund package amount")
        apply_investment_business(
            associate=associate,
            amount=amount,
            reference=f"ADMIN-FT-{entry.id}",
        )

    write_audit(
        actor=actor,
        action="fund.transfer",
        module="wallets",
        object_type="Associate",
        object_id=str(associate.id),
        metadata={
            "amount": str(amount),
            "wallet_type": wallet_type,
            "apply_business": apply_business,
            "payment_method": pay_code,
            "payment_method_label": pay_label,
            "from": source_id or None,
            "company_mint": mint,
        },
    )
    return entry


@transaction.atomic
def associate_fund_transfer(
    *,
    actor,
    to_associate_id: str,
    amount: Decimal,
    narration: str = "",
    payment_method: str = "",
) -> dict:
    """
    Associate transfers a fixed package (min ₹2.20 lakh) to an under-leg member.

    - Debits actor main fund.
    - Credits recipient main fund and records the package as their investment.
    - Self-transfer is not allowed.
    """
    actor_assoc = getattr(actor, "associate", None)
    if not actor_assoc:
        raise PermissionError("Only associates can use associate fund transfer")
    if not actor_assoc.can_fund_transfer:
        raise PermissionError("Fund transfer permission is not enabled for your account")

    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    if not is_fixed_fund_amount(amount):
        raise ValueError(
            "Amount must be one of: 2.20, 4.40, 6.60, 11.00, 22.00, 44.00, 88.00 lakh"
        )

    pay_code = normalize_payment_method(payment_method)
    pay_label = payment_method_label(pay_code)

    recipient = Associate.objects.select_for_update().get(
        associate_id__iexact=str(to_associate_id).strip()
    )
    if recipient.is_deleted:
        raise ValueError("Associate not found")
    if recipient.status in {
        Associate.Status.PENDING,
        Associate.Status.REJECTED,
        Associate.Status.BLOCKED,
    }:
        raise ValueError("Recipient must be Inactive or Active before fund can be applied")
    if recipient.pk == actor_assoc.pk:
        raise ValueError("You cannot transfer funds to yourself")
    if not _recipient_in_leg(actor_associate=actor_assoc, recipient=recipient):
        raise PermissionError("You can only transfer to your under-leg")

    actor_locked = Associate.objects.select_for_update().get(pk=actor_assoc.pk)
    WalletService.ensure_wallets(actor_locked)
    WalletService.ensure_wallets(recipient)

    ref = f"FT-{actor_locked.associate_id}-{recipient.associate_id}"
    label = format_lakh(amount)
    note = (narration or "").strip() or f"Fund transfer {label} via {pay_label}"

    pay_meta = {
        "payment_method": pay_code,
        "payment_method_label": pay_label,
        "fixed_package": True,
        "amount_label": label,
    }

    debit_entry = WalletService.debit(
        associate=actor_locked,
        wallet_type=Wallet.WalletType.MAIN,
        amount=amount,
        reference=ref,
        narration=f"Fund transfer to {recipient.associate_id} via {pay_label}: {note}",
        meta={**pay_meta, "to": recipient.associate_id},
    )

    credit_entry = WalletService.credit(
        associate=recipient,
        wallet_type=Wallet.WalletType.MAIN,
        amount=amount,
        reference=ref,
        narration=f"Fund received from {actor_locked.associate_id} via {pay_label}: {note}",
        meta={**pay_meta, "from": actor_locked.associate_id},
    )

    apply_investment_business(
        associate=recipient,
        amount=amount,
        reference=f"FT-{debit_entry.id}",
    )

    write_audit(
        actor=actor,
        action="fund.transfer.associate",
        module="wallets",
        object_type="Associate",
        object_id=str(recipient.id),
        metadata={
            "amount": str(amount),
            "amount_label": label,
            "from": actor_locked.associate_id,
            "to": recipient.associate_id,
            "self_topup": False,
            "payment_method": pay_code,
            "payment_method_label": pay_label,
        },
    )

    return {
        "debit": debit_entry,
        "credit": credit_entry,
        "amount": amount,
        "amount_label": label,
        "from_associate_id": actor_locked.associate_id,
        "to_associate_id": recipient.associate_id,
        "self_topup": False,
        "payment_method": pay_code,
        "payment_method_label": pay_label,
    }


@transaction.atomic
def create_fund_transfer_request(
    *,
    actor,
    to_associate_id: str,
    amount: Decimal,
    payment_method: str,
    note: str = "",
    utr: str = "",
    proof=None,
) -> FundTransferRequest:
    """Associate asks admin to move a fixed package from their main wallet to an under-leg."""
    if getattr(actor, "is_staff", False) or getattr(actor, "is_superuser", False):
        raise PermissionError("Admin transfers funds directly — do not create a request")
    actor_assoc = getattr(actor, "associate", None)
    if not actor_assoc:
        raise PermissionError("Only associates can request a fund transfer")

    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    if not is_fixed_fund_amount(amount):
        raise ValueError(
            "Amount must be one of: 2.20, 4.40, 6.60, 11.00, 22.00, 44.00, 88.00 lakh"
        )

    pay_code = normalize_payment_method(payment_method)
    beneficiary = Associate.objects.select_for_update().get(
        associate_id__iexact=str(to_associate_id).strip()
    )
    if beneficiary.is_deleted:
        raise ValueError("Associate not found")
    if beneficiary.status in {
        Associate.Status.PENDING,
        Associate.Status.REJECTED,
        Associate.Status.BLOCKED,
    }:
        raise ValueError("Recipient must be Inactive or Active before fund can be requested")
    if beneficiary.pk == actor_assoc.pk:
        raise ValueError("You cannot request a transfer to yourself")
    if not _recipient_in_leg(actor_associate=actor_assoc, recipient=beneficiary):
        raise PermissionError("You can only request a transfer for your under-leg")

    WalletService.ensure_wallets(actor_assoc)
    main = Wallet.objects.select_for_update().get(
        associate=actor_assoc, wallet_type=Wallet.WalletType.MAIN
    )
    available = (main.balance or Decimal("0")) - (main.held_balance or Decimal("0"))
    if available < amount:
        raise ValueError("Not enough balance")

    utr_code = _normalize_utr(utr)
    _validate_proof(proof)

    req = FundTransferRequest.objects.create(
        requester=actor_assoc,
        beneficiary=beneficiary,
        amount=amount,
        wallet_type=Wallet.WalletType.MAIN,
        payment_method=pay_code,
        utr=utr_code,
        proof=proof,
        note=(note or "").strip()[:255],
        status=FundTransferRequest.Status.PENDING,
        apply_business=True,
        created_by=actor,
    )
    write_audit(
        actor=actor,
        action="fund.transfer.request",
        module="wallets",
        object_type="FundTransferRequest",
        object_id=str(req.id),
        metadata={
            "amount": str(amount),
            "from": actor_assoc.associate_id,
            "to": beneficiary.associate_id,
            "payment_method": pay_code,
            "utr": utr_code,
        },
    )
    return req


@transaction.atomic
def approve_fund_transfer_request(
    *,
    request_obj: FundTransferRequest,
    actor,
    apply_business: bool | None = None,
    password: str = "",
) -> FundTransferRequest:
    """Staff-only: debit requester main wallet and credit the under-leg beneficiary."""
    if not (getattr(actor, "is_staff", False) or getattr(actor, "is_superuser", False)):
        raise PermissionError("Only admin can approve fund transfers")
    if not password:
        raise PermissionError("Enter your password to confirm this approval")
    if not actor.check_password(password):
        raise PermissionError("Password is incorrect")
    locked = FundTransferRequest.objects.select_for_update().get(pk=request_obj.pk)
    if locked.status != FundTransferRequest.Status.PENDING:
        raise ValueError("Request is not pending")
    if locked.requester_id == locked.beneficiary_id:
        raise ValueError("Self transfers are not allowed")

    do_business = locked.apply_business if apply_business is None else bool(apply_business)
    if locked.wallet_type != Wallet.WalletType.MAIN:
        do_business = False

    requester = Associate.objects.select_for_update().get(pk=locked.requester_id)
    beneficiary = Associate.objects.select_for_update().get(pk=locked.beneficiary_id)
    WalletService.ensure_wallets(requester)
    WalletService.ensure_wallets(beneficiary)

    pay_label = payment_method_label(locked.payment_method)
    note = locked.note or f"Approved fund transfer request via {pay_label}"
    ref = f"FT-REQ-{locked.id}"
    debit_entry = WalletService.debit(
        associate=requester,
        wallet_type=locked.wallet_type,
        amount=locked.amount,
        reference=ref,
        narration=f"Fund transfer to {beneficiary.associate_id} via {pay_label}: {note}",
        meta={"to": beneficiary.associate_id, "request_id": str(locked.id), "utr": locked.utr},
    )
    entry = WalletService.credit(
        associate=beneficiary,
        wallet_type=locked.wallet_type,
        amount=locked.amount,
        reference=ref,
        narration=f"Fund received from {requester.associate_id} via {pay_label}: {note}",
        meta={"from": requester.associate_id, "request_id": str(locked.id), "utr": locked.utr},
    )
    if do_business:
        apply_investment_business(
            associate=beneficiary,
            amount=locked.amount,
            reference=ref,
        )
    _ = debit_entry
    locked.status = FundTransferRequest.Status.APPROVED
    locked.reviewed_by = actor
    locked.reviewed_at = timezone.now()
    locked.rejection_reason = ""
    locked.ledger_entry = entry
    locked.updated_by = actor
    locked.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "ledger_entry",
            "updated_by",
            "updated_at",
        ]
    )
    write_audit(
        actor=actor,
        action="fund.transfer.request.approve",
        module="wallets",
        object_type="FundTransferRequest",
        object_id=str(locked.id),
        metadata={
            "amount": str(locked.amount),
            "to": locked.beneficiary.associate_id,
            "utr": locked.utr,
            "password_confirmed": True,
        },
    )
    return locked


@transaction.atomic
def reject_fund_transfer_request(
    *,
    request_obj: FundTransferRequest,
    actor,
    reason: str = "",
) -> FundTransferRequest:
    if not (getattr(actor, "is_staff", False) or getattr(actor, "is_superuser", False)):
        raise PermissionError("Only admin can reject fund transfers")
    locked = FundTransferRequest.objects.select_for_update().get(pk=request_obj.pk)
    if locked.status != FundTransferRequest.Status.PENDING:
        raise ValueError("Request is not pending")
    locked.status = FundTransferRequest.Status.REJECTED
    locked.reviewed_by = actor
    locked.reviewed_at = timezone.now()
    locked.rejection_reason = (reason or "Rejected by admin").strip()
    locked.updated_by = actor
    locked.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "updated_by",
            "updated_at",
        ]
    )
    write_audit(
        actor=actor,
        action="fund.transfer.request.reject",
        module="wallets",
        object_type="FundTransferRequest",
        object_id=str(locked.id),
        metadata={"reason": locked.rejection_reason},
    )
    return locked
