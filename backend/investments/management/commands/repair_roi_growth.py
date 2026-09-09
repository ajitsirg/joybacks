"""Fix ROI-on-ROI: claw back investor ₹2,200 Base ROI; keep upline level % only."""

from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q, Sum

from commissions.models import CommissionEntry
from investments.calc import network_level_percent, roi_level_income
from investments.constants import MONTHLY_RETURN_AMOUNT
from wallets.models import LedgerEntry, Wallet
from wallets.services import WalletService


def _debit_safe(*, associate, wallet_type: str, amount: Decimal, reference: str, narration: str) -> None:
    if amount <= 0:
        return
    WalletService.ensure_wallets(associate)
    w = Wallet.objects.filter(associate=associate, wallet_type=wallet_type).first()
    if not w:
        return
    take = min(Decimal(w.balance or 0) - Decimal(w.held_balance or 0), amount)
    if take <= 0:
        return
    try:
        WalletService.debit(
            associate=associate,
            wallet_type=wallet_type,
            amount=take,
            reference=reference,
            narration=narration,
        )
    except ValueError:
        w.balance = max(Decimal("0.00"), Decimal(w.balance or 0) - take)
        w.save(update_fields=["balance", "updated_at"])


def _sync_wallet(w: Wallet) -> Decimal:
    credits = (
        LedgerEntry.objects.filter(
            wallet=w, entry_type=LedgerEntry.EntryType.CREDIT, is_deleted=False
        ).aggregate(s=Sum("amount"))["s"]
        or Decimal("0")
    )
    debits = (
        LedgerEntry.objects.filter(
            wallet=w, entry_type=LedgerEntry.EntryType.DEBIT, is_deleted=False
        ).aggregate(s=Sum("amount"))["s"]
        or Decimal("0")
    )
    return (credits - debits).quantize(Decimal("0.01"))


class Command(BaseCommand):
    help = (
        "Remove investor Base ROI (₹2,200) wallet credits. "
        "ROI wallet keeps upline commission only (₹110, ₹55, …)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")

    @transaction.atomic
    def handle(self, *args, **options):
        dry = bool(options["dry_run"])
        clawed = 0
        clawed_amt = Decimal("0.00")
        fixed = 0
        adjusted_amt = Decimal("0.00")

        # 1) Void L0 Base ROI commission and take the money back
        l0_qs = (
            CommissionEntry.all_objects.filter(level=0, is_deleted=False)
            .filter(
                Q(narration__icontains="Base ROI")
                | Q(reference__startswith="MRI-")
                | Q(reference__startswith="ROI-TO-INC-")
            )
            .exclude(status=CommissionEntry.Status.VOIDED)
            .select_related("beneficiary")
        )
        for e in l0_qs:
            amt = Decimal(e.amount or 0)
            ben = e.beneficiary
            if not ben or amt <= 0:
                continue
            self.stdout.write(f"  claw L0 ₹{amt} from {ben.associate_id} {e.wallet_type} ({e.reference})")
            if not dry:
                _debit_safe(
                    associate=ben,
                    wallet_type=e.wallet_type,
                    amount=amt,
                    reference=f"ROI-CLAW-{e.id}",
                    narration="Reverse investor Base ROI — not a payout",
                )
                e.status = CommissionEntry.Status.VOIDED
                e.save(update_fields=["status", "updated_at"])
            clawed += 1
            clawed_amt += amt

        # 2) Correct upline amounts if anyone was paid full ₹2,200 as level income
        qs = (
            CommissionEntry.all_objects.filter(
                wallet_type=Wallet.WalletType.ROI,
                level__gte=1,
                is_deleted=False,
            )
            .exclude(status=CommissionEntry.Status.VOIDED)
            .select_related("beneficiary")
        )
        for e in qs:
            depth = int(e.level or 0)
            if depth < 1:
                continue
            base = Decimal(e.monthly_return_amount or MONTHLY_RETURN_AMOUNT)
            expected = roi_level_income(base_roi=base, network_level=depth)
            actual = Decimal(e.amount or 0)
            if actual == expected:
                continue
            diff = actual - expected
            ben = e.beneficiary
            if ben and not ben.is_deleted and diff != 0:
                self.stdout.write(
                    f"  fix {ben.associate_id} L{depth} {actual} → {expected} ({e.reference})"
                )
                if not dry:
                    if diff > 0:
                        _debit_safe(
                            associate=ben,
                            wallet_type=Wallet.WalletType.ROI,
                            amount=diff,
                            reference=f"ROI-FIX-{e.id}",
                            narration=f"Correct ROI-on-ROI L{depth}",
                        )
                    else:
                        WalletService.ensure_wallets(ben)
                        WalletService.credit(
                            associate=ben,
                            wallet_type=Wallet.WalletType.ROI,
                            amount=-diff,
                            reference=f"ROI-FIX-{e.id}",
                            narration=f"Correct ROI-on-ROI L{depth}",
                        )
                    e.amount = expected
                    e.growth_level = depth
                    e.percent = network_level_percent(depth)
                    e.narration = (
                        f"ROI-on-ROI L{depth} ({e.percent}%) on base ROI ₹{base} "
                        f"= ₹{expected} [corrected]"
                    )
                    e.save(update_fields=["amount", "growth_level", "percent", "narration", "updated_at"])
                adjusted_amt += abs(diff)
                fixed += 1

        synced = 0
        for wtype in (Wallet.WalletType.ROI, Wallet.WalletType.INCOME):
            for w in Wallet.all_objects.filter(wallet_type=wtype, is_deleted=False):
                if w.associate.is_deleted:
                    if not dry and w.balance != 0:
                        w.balance = Decimal("0.00")
                        w.save(update_fields=["balance", "updated_at"])
                    continue
                net = _sync_wallet(w)
                if net != Decimal(w.balance or 0):
                    self.stdout.write(f"  sync {w.associate.associate_id} {wtype} {w.balance} → {net}")
                    if not dry:
                        w.balance = net
                        w.save(update_fields=["balance", "updated_at"])
                    synced += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{'DRY ' if dry else ''}l0_clawed={clawed} clawed_amt={clawed_amt} "
                f"entries_fixed={fixed} delta={adjusted_amt} wallets_synced={synced}"
            )
        )
