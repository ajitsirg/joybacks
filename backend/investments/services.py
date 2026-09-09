"""Create investment contracts and process monthly ROI + growth-level upline commission."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Count, Sum
from django.utils import timezone

from associates.models import Associate
from commissions.models import CommissionEntry, CommissionRun
from commissions.services import CommissionEngine, can_receive_payout
from configuration.repository import ConfigRepository
from genealogy.services import GenealogyService
from investments.calc import base_roi_amount, default_monthly_return, roi_level_income, roi_rate_percent
from investments.constants import (
    INVESTMENT_PRINCIPAL,
    MAX_GROWTH_LEVELS,
    RETURN_MONTHS,
)
from investments.models import InvestmentContract
from wallets.models import Wallet


def _add_one_month(d: date) -> date:
    """Advance calendar month, clamping day to 28 for safety."""
    month = d.month + 1
    year = d.year
    if month > 12:
        month = 1
        year += 1
    day = min(d.day, 28)
    return date(year, month, day)


@transaction.atomic
def create_investment_contracts(
    *,
    associate: Associate,
    amount: Decimal,
    reference: str,
    start_on: date | None = None,
) -> list[InvestmentContract]:
    """
    Create one 48-month contract per whole ₹2.2L unit in `amount`.
    Idempotent on (source_reference, unit_index).
    """
    amount = Decimal(str(amount))
    units = int(amount // INVESTMENT_PRINCIPAL)
    if units <= 0:
        return []

    start = start_on or timezone.localdate()
    created: list[InvestmentContract] = []
    for idx in range(1, units + 1):
        if InvestmentContract.objects.filter(source_reference=reference, unit_index=idx).exists():
            continue
        monthly = base_roi_amount(INVESTMENT_PRINCIPAL)
        try:
            contract = InvestmentContract.objects.create(
                associate=associate,
                principal=INVESTMENT_PRINCIPAL,
                monthly_return=monthly,
                months_total=RETURN_MONTHS,
                months_paid=0,
                unit_index=idx,
                source_reference=reference,
                started_on=start,
                next_payout_on=start,
                status=InvestmentContract.Status.ACTIVE,
            )
            created.append(contract)
        except IntegrityError:
            continue

    # Month-1 ROI credits immediately so ROI fund updates on investment
    for contract in created:
        process_monthly_return(contract, as_of=start)

    return created


@transaction.atomic
def process_monthly_return(
    contract: InvestmentContract,
    *,
    as_of: date | None = None,
) -> CommissionRun | None:
    """
    Pay upline ROI-on-ROI only. Investor is never credited ₹2,200.

    Base ROI = Investment × ROI Rate / 100  (e.g. ₹2.2L × 1% = ₹2,200)
    Level N income = Base ROI × Level N % / 100  (NOT investment × level %)
    ₹2,200 is the calculation base only — not a wallet payout.
    """
    as_of = as_of or timezone.localdate()
    contract = InvestmentContract.objects.select_for_update().get(pk=contract.pk)

    if contract.status != InvestmentContract.Status.ACTIVE:
        return None
    if contract.months_paid >= contract.months_total:
        contract.status = InvestmentContract.Status.COMPLETED
        contract.save(update_fields=["status", "updated_at"])
        return None
    if contract.next_payout_on > as_of:
        return None

    month_index = int(contract.months_paid) + 1
    principal = Decimal(contract.principal or INVESTMENT_PRINCIPAL)
    monthly = Decimal(contract.monthly_return or 0)
    if monthly <= 0:
        monthly = base_roi_amount(principal)
    monthly = monthly.quantize(Decimal("0.01"))
    roi_pct = roi_rate_percent()
    investor = Associate.objects.select_for_update().get(pk=contract.associate_id)
    commission_month = date(as_of.year, as_of.month, 1)
    ref_base = f"MRI-{contract.id}-M{month_index}"

    already_paid = (
        CommissionEntry.objects.filter(
            investment=contract,
            month_index=month_index,
        )
        .exclude(status=CommissionEntry.Status.VOIDED)
        .exists()
    )
    if already_paid:
        return None

    run = CommissionRun.objects.create(
        run_type=CommissionRun.RunType.ROI,
        status=CommissionRun.Status.PENDING,
        source_reference=ref_base,
        source_amount=monthly,
        notes=(
            f"ROI-on-ROI M{month_index}/{contract.months_total} "
            f"investment={contract.id} base_roi={monthly} (not paid to investor)"
        ),
    )

    # Upline only: Level N = Base ROI × Level N % / 100. Investor gets ₹0.
    # Depth D pays the Dth ancestor only if they have N immediate children
    # (qualified directs ≥ slab.required_directs, 0 means use the level number).
    # Ineligible = skip, no compression.
    skipped_ineligible = 0
    upline = GenealogyService.upline(investor, max_levels=MAX_GROWTH_LEVELS)
    for link in upline:
        depth = int(link.depth)
        if depth < 1 or depth > MAX_GROWTH_LEVELS:
            continue
        beneficiary = link.ancestor
        if not can_receive_payout(beneficiary):
            continue
        unlocked = CommissionEngine.unlocked_performance_levels(beneficiary)
        if depth > unlocked:
            skipped_ineligible += 1
            continue

        percent = ConfigRepository.performance_percent(depth)
        if percent <= 0:
            from investments.constants import DEFAULT_GROWTH_PERCENTS

            percent = dict(DEFAULT_GROWTH_PERCENTS).get(depth, Decimal("0"))
        if percent <= 0:
            continue

        payout = roi_level_income(base_roi=monthly, network_level=depth)
        if payout <= 0:
            continue

        ref_up = f"{ref_base}-L{depth}"
        if CommissionEntry.objects.filter(
            beneficiary=beneficiary,
            level=depth,
            reference=ref_up,
        ).exclude(status=CommissionEntry.Status.VOIDED).exists():
            continue

        try:
            with transaction.atomic():
                entry = CommissionEntry.objects.create(
                    run=run,
                    beneficiary=beneficiary,
                    source_associate=investor,
                    level=depth,
                    growth_level=depth,
                    percent=percent,
                    sale_amount=principal,
                    monthly_return_amount=monthly,
                    commission_month=commission_month,
                    month_index=month_index,
                    investment=contract,
                    amount=payout,
                    wallet_type=Wallet.WalletType.ROI,
                    reference=ref_up,
                    status=CommissionEntry.Status.CREDITED,
                    narration=(
                        f"Level {depth} ROI Income — {percent}% of base ROI ₹{monthly} "
                        f"= ₹{payout} from {investor.associate_id}"
                    ),
                )
                from commissions.charges import credit_commission

                credit_commission(
                    associate=beneficiary,
                    wallet_type=Wallet.WalletType.ROI,
                    gross=payout,
                    reference=ref_up,
                    narration=f"Level {depth} ROI Income from {investor.associate_id}",
                    kind="roi",
                    commission_entry=entry,
                    meta={
                        "investment_id": str(contract.id),
                        "month_index": month_index,
                        "network_level": depth,
                        "base_roi": str(monthly),
                        "roi_rate": str(roi_pct),
                        "run_id": str(run.id),
                    },
                )
        except IntegrityError:
            continue

    contract.months_paid = month_index
    contract.last_payout_on = as_of
    contract.next_payout_on = _add_one_month(contract.next_payout_on)
    fields = ["months_paid", "last_payout_on", "next_payout_on", "updated_at"]
    if contract.months_paid >= contract.months_total:
        contract.status = InvestmentContract.Status.COMPLETED
        fields.append("status")
    contract.save(update_fields=fields)

    credited = run.entries.exclude(status=CommissionEntry.Status.VOIDED)
    paid = credited.aggregate(total=Sum("amount"), n=Count("id"), people=Count("beneficiary_id", distinct=True))
    level_bits = []
    for lv in range(1, MAX_GROWTH_LEVELS + 1):
        lv_amt = credited.filter(level=lv).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        if lv_amt:
            level_bits.append(f"L{lv}={lv_amt}")
    run.status = CommissionRun.Status.COMPLETED
    run.notes = (
        f"ROI-on-ROI M{month_index}/{contract.months_total} "
        f"investment={contract.id} base_roi={monthly} (not paid to investor); "
        f"total_roi_generated={monthly} total_level_commission={paid['total'] or 0} "
        f"beneficiaries={paid['people'] or 0} successful={paid['n'] or 0} "
        f"skipped_ineligible={skipped_ineligible} "
        + (" ".join(level_bits) if level_bits else "no-level-payouts")
    )
    run.save(update_fields=["status", "notes", "updated_at"])
    return run


def process_due_monthly_returns(*, as_of: date | None = None, limit: int = 0) -> dict:
    """Process all active contracts due on/before as_of."""
    as_of = as_of or timezone.localdate()
    qs = (
        InvestmentContract.objects.filter(
            status=InvestmentContract.Status.ACTIVE,
            next_payout_on__lte=as_of,
        )
        .select_related("associate")
        .order_by("next_payout_on", "created_at")
    )
    if limit > 0:
        qs = qs[:limit]

    paid = 0
    skipped = 0
    for contract in qs:
        # Loop until caught up (missed months) or completed
        safety = 0
        while safety < RETURN_MONTHS:
            safety += 1
            contract.refresh_from_db()
            if contract.status != InvestmentContract.Status.ACTIVE:
                break
            if contract.next_payout_on > as_of:
                break
            result = process_monthly_return(contract, as_of=as_of)
            if result is None:
                skipped += 1
                break
            paid += 1
    return {"as_of": str(as_of), "payouts": paid, "skipped": skipped}
