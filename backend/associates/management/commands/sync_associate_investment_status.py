"""Mark No-Investment (gray) associates Inactive; Active only at ₹2.2L+ investment."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from associates.models import Associate


class Command(BaseCommand):
    help = (
        "Resync associate flag + status from investment: "
        "gray / under ₹2.2L → Inactive; ₹2.2L+ → Active "
        "(pending/rejected/blocked unchanged)."
    )

    def handle(self, *args, **options):
        updated = 0
        samples: list[str] = []
        for assoc in Associate.all_objects.exclude(
            status__in=[
                Associate.Status.PENDING,
                Associate.Status.REJECTED,
                Associate.Status.BLOCKED,
            ]
        ).iterator():
            before = (assoc.status, assoc.flag_color)
            assoc.sync_status_from_investment(save=True)
            after = (assoc.status, assoc.flag_color)
            if before != after:
                updated += 1
                if len(samples) < 25:
                    samples.append(f"{assoc.associate_id}: {before} → {after}")

        active = Associate.objects.filter(status=Associate.Status.ACTIVE).count()
        inactive = Associate.objects.filter(status=Associate.Status.INACTIVE).count()
        gray = Associate.objects.filter(flag_color=Associate.FlagColor.GRAY).count()
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} associates"))
        for line in samples:
            self.stdout.write(f"  {line}")
        self.stdout.write(f"Live counts — active={active} inactive={inactive} gray_flag={gray}")
