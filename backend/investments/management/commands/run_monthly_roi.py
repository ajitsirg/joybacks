"""Process due monthly ROI (₹2,200) + growth-level upline commissions."""

from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from investments.services import process_due_monthly_returns


class Command(BaseCommand):
    help = (
        "Credit due monthly investment returns (₹2,200 × up to 48 months) "
        "and Growth Level upline commissions"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--as-of",
            type=str,
            default="",
            help="Process as of YYYY-MM-DD (default: today)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Max contracts to scan (0 = all due)",
        )

    def handle(self, *args, **options):
        as_of = timezone.localdate()
        raw = (options.get("as_of") or "").strip()
        if raw:
            as_of = date.fromisoformat(raw)
        result = process_due_monthly_returns(as_of=as_of, limit=int(options.get("limit") or 0))
        self.stdout.write(
            self.style.SUCCESS(
                f"Monthly ROI done as_of={result['as_of']} "
                f"payouts={result['payouts']} skipped={result['skipped']}"
            )
        )
