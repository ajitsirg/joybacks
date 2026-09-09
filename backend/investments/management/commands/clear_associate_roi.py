"""Clear ROI wallet + ROI commission history for one associate (admin debug / retest)."""

from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from associates.models import Associate
from commissions.models import CommissionEntry
from investments.models import InvestmentContract
from wallets.models import LedgerEntry, Wallet
from wallets.services import WalletService


class Command(BaseCommand):
    help = "Reset ROI wallet, ledger, and ROI commission rows for one associate (retest ROI-on-ROI)."

    def add_arguments(self, parser):
        parser.add_argument("associate_id", help="e.g. JOY9602193825")
        parser.add_argument(
            "--hard",
            action="store_true",
            help="Permanently delete ledger/commission rows (default: soft-archive)",
        )
        parser.add_argument(
            "--include-contracts",
            action="store_true",
            help="Also archive investment contracts (resets month-1 ROI source)",
        )
        parser.add_argument("--dry-run", action="store_true", help="Report only")

    @transaction.atomic
    def handle(self, *args, **options):
        aid = str(options["associate_id"]).strip().upper()
        hard = bool(options["hard"])
        dry = bool(options["dry_run"])
        include_contracts = bool(options["include_contracts"])

        assoc = Associate.all_objects.filter(associate_id__iexact=aid).first()
        if not assoc:
            raise SystemExit(f"Associate not found: {aid}")

        WalletService.ensure_wallets(assoc)
        roi_wallet = Wallet.all_objects.filter(
            associate=assoc, wallet_type=Wallet.WalletType.ROI
        ).first()

        ledger_qs = LedgerEntry.all_objects.filter(wallet=roi_wallet) if roi_wallet else LedgerEntry.all_objects.none()
        commission_qs = CommissionEntry.all_objects.filter(
            Q(beneficiary=assoc) | Q(source_associate=assoc),
            wallet_type=Wallet.WalletType.ROI,
        ).exclude(status=CommissionEntry.Status.VOIDED)
        contract_qs = InvestmentContract.all_objects.filter(associate=assoc)

        self.stdout.write(f"Associate: {aid} (pk={assoc.pk})")
        self.stdout.write(f"  ROI wallet balance: {roi_wallet.balance if roi_wallet else 'n/a'}")
        self.stdout.write(f"  ROI ledger rows: {ledger_qs.filter(is_deleted=False).count()} live / {ledger_qs.count()} total")
        self.stdout.write(f"  ROI commissions: {commission_qs.count()}")
        for e in commission_qs.order_by("-created_at")[:15]:
            self.stdout.write(
                f"    L{e.level} ₹{e.amount} ref={e.reference} "
                f"ben={e.beneficiary.associate_id} src={e.source_associate.associate_id if e.source_associate_id else '-'}"
            )
        if commission_qs.count() > 15:
            self.stdout.write(f"    … and {commission_qs.count() - 15} more")

        if dry:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes"))
            return

        ledger_n = commission_n = contract_n = 0

        if roi_wallet:
            if hard:
                ledger_n = ledger_qs.count()
                ledger_qs.delete(force=True)
                roi_wallet.balance = Decimal("0.00")
                roi_wallet.held_balance = Decimal("0.00")
                roi_wallet.is_deleted = False
                roi_wallet.deleted_at = None
                roi_wallet.save(
                    update_fields=[
                        "balance",
                        "held_balance",
                        "is_deleted",
                        "deleted_at",
                        "updated_at",
                    ]
                )
            else:
                ledger_n = ledger_qs.filter(is_deleted=False).count()
                ledger_qs.filter(is_deleted=False).delete(soft=True)
                roi_wallet.balance = Decimal("0.00")
                roi_wallet.held_balance = Decimal("0.00")
                roi_wallet.is_deleted = False
                roi_wallet.deleted_at = None
                roi_wallet.save(
                    update_fields=[
                        "balance",
                        "held_balance",
                        "is_deleted",
                        "deleted_at",
                        "updated_at",
                    ]
                )

        for entry in commission_qs:
            if hard:
                entry.delete(force=True)
            else:
                entry.status = CommissionEntry.Status.VOIDED
                entry.save(update_fields=["status", "updated_at"])
            commission_n += 1

        if include_contracts:
            if hard:
                contract_n = contract_qs.count()
                contract_qs.delete(force=True)
            else:
                contract_n = contract_qs.filter(is_deleted=False).count()
                contract_qs.filter(is_deleted=False).delete(soft=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Cleared {aid}: ledger={ledger_n} commissions={commission_n} "
                f"contracts={contract_n} hard={hard} roi_balance=0"
            )
        )
