"""Backfill InvestmentContract rows for associates with qualifying ₹2.2L units."""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from associates.models import Associate
from investments.constants import INVESTMENT_PRINCIPAL
from investments.models import InvestmentContract
from investments.services import create_investment_contracts


class Command(BaseCommand):
    help = "Create missing 48-month investment contracts from personal_business units"

    def add_arguments(self, parser):
        parser.add_argument("--associate-id", type=str, default="", help="Limit to one associate ID")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        qs = Associate.objects.filter(is_deleted=False).order_by("associate_id")
        aid = (options.get("associate_id") or "").strip()
        if aid:
            qs = qs.filter(associate_id__iexact=aid)

        created_total = 0
        for assoc in qs.iterator():
            invested = assoc.invested_amount()
            units = int(invested // INVESTMENT_PRINCIPAL)
            if units <= 0:
                continue
            existing = InvestmentContract.objects.filter(associate=assoc).count()
            missing = units - existing
            if missing <= 0:
                continue
            if options["dry_run"]:
                self.stdout.write(f"{assoc.associate_id}: would create {missing} contract(s)")
                created_total += missing
                continue
            # Create only missing units under a stable backfill reference
            ref = f"BACKFILL-{assoc.associate_id}"
            # unit_index continues after existing for this ref, or use new indices 1..missing
            # Prefer create_investment_contracts with amount = missing * principal
            # but unique is (source_reference, unit_index) — existing backfill may partially exist
            made = create_investment_contracts(
                associate=assoc,
                amount=Decimal(INVESTMENT_PRINCIPAL) * missing,
                reference=ref,
                start_on=timezone.localdate(),
            )
            # If some unit_indexes already exist, create remaining with suffix
            still = missing - len(made)
            idx = InvestmentContract.objects.filter(associate=assoc).count() + 1
            while still > 0:
                ref2 = f"BACKFILL-{assoc.associate_id}-U{idx}"
                more = create_investment_contracts(
                    associate=assoc,
                    amount=INVESTMENT_PRINCIPAL,
                    reference=ref2,
                    start_on=timezone.localdate(),
                )
                if not more:
                    break
                made.extend(more)
                still -= len(more)
                idx += 1
            created_total += len(made)
            if made:
                self.stdout.write(f"{assoc.associate_id}: created {len(made)}")

        self.stdout.write(self.style.SUCCESS(f"Backfill done. contracts={created_total}"))
