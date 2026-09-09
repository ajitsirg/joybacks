"""Commission engine — level % from configuration; unlock by direct farmhouse sales."""

from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError, transaction

from associates.models import Associate
from commissions.constants import FARHOUSE_SALE_AMOUNT, MAX_COMMISSION_LEVELS
from commissions.models import CommissionEntry, CommissionRun
from configuration.repository import ConfigRepository
from genealogy.services import GenealogyService
from investments.constants import MAX_GROWTH_LEVELS
from wallets.models import Wallet

# Only Active members earn sale / ROI. Inactive is blocked (tester rule).
PAYOUT_BLOCKED_STATUSES = {
    Associate.Status.PENDING,
    Associate.Status.REJECTED,
    Associate.Status.BLOCKED,
    Associate.Status.INACTIVE,
}


def can_receive_payout(associate: Associate) -> bool:
    if getattr(associate, "is_deleted", False):
        return False
    return associate.status not in PAYOUT_BLOCKED_STATUSES


class CommissionEngine:
    @staticmethod
    def qualifying_sale_units(associate: Associate) -> int:
        """How many ₹2.2L farmhouse units this associate has personally completed."""
        invested = associate.invested_amount()
        if invested <= 0:
            return 0
        return int(invested // FARHOUSE_SALE_AMOUNT)

    @staticmethod
    def qualifying_direct_sales_count(associate: Associate) -> int:
        """
        Immediate children who each have ≥1 ₹2.2L farmhouse unit.

        Level N sale commission and ROI both unlock from this headcount
        (not the sum of units — one child with 5 units still counts as 1).
        """
        return CommissionEngine.growth_level(associate)

    @staticmethod
    def growth_level(associate: Associate) -> int:
        """
        Growth Level 1–10 from number of *direct people* with ≥1 qualifying farmhouse sale.

        Same headcount as qualifying_direct_sales_count.
        """
        count = 0
        directs = Associate.objects.filter(sponsor_id=associate.pk, is_deleted=False).only(
            "personal_business", "join_amount"
        )
        for direct in directs:
            if CommissionEngine.qualifying_sale_units(direct) >= 1:
                count += 1
        return min(MAX_GROWTH_LEVELS, count)

    @staticmethod
    def unlocked_performance_levels(associate: Associate) -> int:
        """
        Highest ROI-on-ROI depth this associate may receive.

        Uses PerformanceIncomeSlab.required_directs (default = level number).
        Unlock is progressive: N qualified directs → levels 1..N. Ineligible
        depths are skipped (no spillover / compression to the next upline).
        Qualified direct = existing growth_level definition (direct with ≥1
        ₹2.2L farmhouse unit).
        """
        growth = CommissionEngine.growth_level(associate)
        plan = ConfigRepository.active_performance_plan()
        if not plan:
            return min(MAX_GROWTH_LEVELS, growth)
        unlocked = 0
        slabs = list(plan.slabs.filter(is_active=True, is_deleted=False).order_by("level"))
        if not slabs:
            return min(MAX_GROWTH_LEVELS, growth)
        for slab in slabs:
            need = int(slab.required_directs or 0) or int(slab.level)
            if growth >= need:
                unlocked = int(slab.level)
            else:
                break
        return min(MAX_GROWTH_LEVELS, unlocked)

    @staticmethod
    def unlocked_commission_levels(associate: Associate) -> int:
        """
        Dynamic unlock: N immediate children with a farmhouse unit → levels 1..N
        (capped at plan max / 5). Same headcount rule as ROI-on-ROI.

        0 children → no level income; 5+ children → all five levels.
        """
        plan = ConfigRepository.active_level_plan()
        max_levels = int(plan.max_levels) if plan else MAX_COMMISSION_LEVELS
        max_levels = min(max_levels, MAX_COMMISSION_LEVELS) if max_levels > 0 else MAX_COMMISSION_LEVELS
        return min(max_levels, CommissionEngine.growth_level(associate))

    @staticmethod
    @transaction.atomic
    def distribute_level_income(
        *,
        source_associate: Associate,
        amount: Decimal,
        reference: str,
    ) -> CommissionRun:
        """
        Pay upline level income on a completed qualifying sale.

        Each upline earns only for network depths they have unlocked via their own
        direct farmhouse sales. Duplicate (beneficiary, level, reference) rows are skipped.
        """
        plan = ConfigRepository.active_level_plan()
        run = CommissionRun.objects.create(
            run_type=CommissionRun.RunType.LEVEL,
            status=CommissionRun.Status.PENDING,
            source_reference=reference,
            source_amount=amount,
            notes=f"Plan={plan.code if plan else 'none'}; farmhouse_unit={FARHOUSE_SALE_AMOUNT}",
        )
        if amount <= 0:
            run.status = CommissionRun.Status.COMPLETED
            run.save(update_fields=["status", "updated_at"])
            return run

        # Only whole farmhouse units generate level income (partial deposits do not)
        units = int(amount // FARHOUSE_SALE_AMOUNT)
        if units <= 0:
            run.notes = (run.notes or "") + "; skipped: below farmhouse sale amount"
            run.status = CommissionRun.Status.COMPLETED
            run.save(update_fields=["status", "notes", "updated_at"])
            return run

        sale_amount = (FARHOUSE_SALE_AMOUNT * units).quantize(Decimal("0.01"))
        max_levels = int(plan.max_levels) if plan else MAX_COMMISSION_LEVELS
        max_levels = min(max_levels, MAX_COMMISSION_LEVELS) if max_levels > 0 else MAX_COMMISSION_LEVELS
        upline = GenealogyService.upline(source_associate, max_levels=max_levels)

        for link in upline:
            depth = int(link.depth)
            if depth < 1 or depth > max_levels:
                continue

            beneficiary = link.ancestor
            if not can_receive_payout(beneficiary):
                continue

            unlocked = CommissionEngine.unlocked_commission_levels(beneficiary)
            if depth > unlocked:
                continue

            percent = ConfigRepository.level_percent(depth)
            if percent <= 0:
                continue

            payout = (sale_amount * percent / Decimal("100")).quantize(Decimal("0.01"))
            if payout <= 0:
                continue

            # Prevent duplicate commission for the same sale/level/upline
            if CommissionEntry.objects.filter(
                beneficiary=beneficiary,
                level=depth,
                reference=reference,
            ).exclude(status=CommissionEntry.Status.VOIDED).exists():
                continue

            try:
                with transaction.atomic():
                    entry = CommissionEntry.objects.create(
                        run=run,
                        beneficiary=beneficiary,
                        source_associate=source_associate,
                        level=depth,
                        percent=percent,
                        sale_amount=sale_amount,
                        amount=payout,
                        wallet_type=Wallet.WalletType.INCOME,
                        reference=reference,
                        status=CommissionEntry.Status.CREDITED,
                        narration=(
                            f"Level {depth} ({percent}%) on ₹{sale_amount} "
                            f"from {source_associate.associate_id}"
                        ),
                    )
                    from commissions.charges import credit_commission

                    credit_commission(
                        associate=beneficiary,
                        wallet_type=Wallet.WalletType.INCOME,
                        gross=payout,
                        reference=f"{reference}-L{depth}",
                        narration=f"Level {depth} farmhouse commission from {source_associate.associate_id}",
                        kind="income",
                        commission_entry=entry,
                        meta={
                            "run_id": str(run.id),
                            "percent": str(percent),
                            "sale_amount": str(sale_amount),
                            "network_level": depth,
                            "buyer_id": source_associate.associate_id,
                        },
                    )
            except IntegrityError:
                # Same beneficiary/level/reference already credited
                continue

        summary = run.payout_summary()
        run.status = CommissionRun.Status.COMPLETED
        run.notes = (
            f"{run.notes or ''}; total_sale={sale_amount} "
            f"total_level_commission={summary['total_level_commission']} "
            f"beneficiaries={summary['beneficiaries']} "
            f"successful={summary['successful_entries']}"
        ).strip("; ")
        run.save(update_fields=["status", "notes", "updated_at"])
        return run

    @staticmethod
    @transaction.atomic
    def distribute_roi(*, associate: Associate, base_amount: Decimal, reference: str) -> CommissionRun:
        plan = ConfigRepository.active_roi_plan()
        run = CommissionRun.objects.create(
            run_type=CommissionRun.RunType.ROI,
            status=CommissionRun.Status.PENDING,
            source_reference=reference,
            source_amount=base_amount,
        )
        if not plan or associate.status != Associate.Status.ACTIVE:
            run.status = CommissionRun.Status.COMPLETED
            run.save(update_fields=["status", "updated_at"])
            return run

        # Base ROI is a calculation input only — never paid to the investor.
        run.status = CommissionRun.Status.COMPLETED
        run.notes = (run.notes or "") + "; investor Base ROI not paid (ROI-on-ROI upline only)"
        run.save(update_fields=["status", "notes", "updated_at"])
        return run
