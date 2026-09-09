"""Recalculate Reward Achievement (40/30/30) and pay any missing cash."""

from django.core.management.base import BaseCommand

from associates.models import Associate


class Command(BaseCommand):
    help = "Sync reward levels from 40/30/30 legs and credit unpaid Reward wallet amounts."

    def add_arguments(self, parser):
        parser.add_argument("--associate-id", help="Only this associate ID")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        qs = Associate.objects.filter(is_deleted=False).order_by("created_at")
        if options.get("associate_id"):
            qs = qs.filter(associate_id__iexact=options["associate_id"].strip())
        dry = bool(options["dry_run"])
        updated = paid_n = 0
        from associates.rewards import compute_reward_level_for, pay_unlocked_rewards
        from configuration.rewards import sync_official_milestones

        if not dry:
            sync_official_milestones()

        for assoc in qs.iterator():
            level, name = compute_reward_level_for(assoc)
            if assoc.earning_level != level or assoc.earning_level_name != name:
                self.stdout.write(f"  {assoc.associate_id} {assoc.earning_level_name} → {name}")
                if not dry:
                    assoc.earning_level = level
                    assoc.earning_level_name = name
                    assoc.save(update_fields=["earning_level", "earning_level_name", "updated_at"])
                updated += 1
            if level > 0 and not dry:
                n = pay_unlocked_rewards(associate=assoc, old_level=0, new_level=level)
                paid_n += n
                if n:
                    self.stdout.write(f"    paid {n} slab(s) to {assoc.associate_id}")
        self.stdout.write(self.style.SUCCESS(f"{'DRY ' if dry else ''}levels={updated} payouts={paid_n}"))
