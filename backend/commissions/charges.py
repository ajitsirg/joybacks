"""Company admin charge on sale, ROI, and reward commissions."""

from __future__ import annotations

from decimal import Decimal

from wallets.models import LedgerEntry
from wallets.services import WalletService

DEFAULT_ADMIN_CHARGE_PERCENT = Decimal("10.00")


def admin_charge_percent() -> Decimal:
    try:
        from configuration.models import CompanySettings

        row = CompanySettings.objects.filter(is_active=True).order_by("created_at").first()
        if row is not None and row.admin_charge_percent is not None:
            return Decimal(row.admin_charge_percent)
    except Exception:
        pass
    return DEFAULT_ADMIN_CHARGE_PERCENT


def split_admin_charge(gross: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    """Return (net, charge, percent). Associates receive net only."""
    amount = Decimal(str(gross)).quantize(Decimal("0.01"))
    pct = admin_charge_percent()
    if amount <= 0 or pct <= 0:
        return amount, Decimal("0.00"), pct
    charge = (amount * pct / Decimal("100")).quantize(Decimal("0.01"))
    if charge >= amount:
        charge = amount - Decimal("0.01") if amount > Decimal("0.01") else Decimal("0.00")
    net = (amount - charge).quantize(Decimal("0.01"))
    return net, charge, pct


def net_after_charge(gross: Decimal) -> Decimal:
    return split_admin_charge(gross)[0]


def credit_commission(
    *,
    associate,
    wallet_type: str,
    gross: Decimal,
    reference: str,
    narration: str,
    kind: str,
    commission_entry=None,
    meta: dict | None = None,
) -> LedgerEntry:
    """Credit the associate the net amount and store a staff-only admin charge row."""
    from commissions.models import AdminCharge

    net, charge, pct = split_admin_charge(gross)
    extra = {
        **(meta or {}),
        "gross_amount": str(gross),
        "admin_charge": str(charge),
        "admin_charge_percent": str(pct),
        "net_amount": str(net),
    }
    ledger = WalletService.credit(
        associate=associate,
        wallet_type=wallet_type,
        amount=net,
        reference=reference,
        narration=narration,
        meta=extra,
    )
    if commission_entry is not None:
        commission_entry.admin_charge_amount = charge
        commission_entry.net_amount = net
        commission_entry.save(update_fields=["admin_charge_amount", "net_amount", "updated_at"])
    if charge > 0:
        AdminCharge.objects.create(
            associate=associate,
            kind=kind,
            wallet_type=wallet_type,
            gross_amount=Decimal(str(gross)).quantize(Decimal("0.01")),
            charge_percent=pct,
            charge_amount=charge,
            net_amount=net,
            reference=reference,
            narration=f"Admin charge {pct}% on {narration}"[:255],
            commission_entry=commission_entry,
            ledger_entry=ledger,
        )
    return ledger
