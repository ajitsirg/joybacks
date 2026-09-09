"""Remove seeded demo associates so Associate Tree shows only real members."""

from __future__ import annotations

from collections import deque

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from associates.models import Associate
from configuration.models import GenealogySettings
from configuration.repository import ConfigRepository
from genealogy.models import GenealogyClosure, GenealogyNode
from genealogy.services import GenealogyService

User = get_user_model()

DEMO_ID_PREFIXES = ("JOYDEMO", "JOY1000")
DEMO_EMAIL_SUFFIX = "@joyclub.demo"


class Command(BaseCommand):
    help = "Purge JOYDEMO* / JOY1000* seed associates and rebuild real genealogy"

    def add_arguments(self, parser):
        parser.add_argument(
            "--hard",
            action="store_true",
            help="Hard-delete demo rows (default: soft-delete + detach genealogy)",
        )

    def handle(self, *args, **options):
        hard = bool(options["hard"])
        demos = list(
            Associate.all_objects.filter(
                Q(associate_id__startswith="JOYDEMO")
                | Q(associate_id__startswith="JOY1000")
                | Q(user__email__iendswith=DEMO_EMAIL_SUFFIX)
            ).select_related("user")
        )
        if not demos:
            self.stdout.write("No demo associates found")
        else:
            self.stdout.write(f"Purging {len(demos)} demo associates…")

        with transaction.atomic():
            # Detach deepest first so PROTECT parent links don't block
            demo_ids = {d.id for d in demos}
            ordered = sorted(
                demos,
                key=lambda a: getattr(getattr(a, "genealogy_node", None), "depth", 0),
                reverse=True,
            )
            for assoc in ordered:
                GenealogyService.hard_detach(assoc)
                # Clear sponsor links pointing at this demo from non-demo rows
                Associate.all_objects.filter(sponsor=assoc).exclude(id__in=demo_ids).update(
                    sponsor=None,
                    sponsor_associate_id="",
                )
                if hard:
                    user = assoc.user
                    assoc.delete(soft=False)
                    if user and not user.is_staff and not user.is_superuser:
                        user.delete()
                else:
                    assoc.is_deleted = True
                    from django.utils import timezone

                    assoc.deleted_at = timezone.now()
                    assoc.status = Associate.Status.INACTIVE
                    assoc.save(update_fields=["is_deleted", "deleted_at", "status", "updated_at"])
                    u = assoc.user
                    if u and not u.is_staff:
                        u.is_active = False
                        u.save(update_fields=["is_active"])
                self.stdout.write(f"  removed {assoc.associate_id}")

            self._rebuild_genealogy()

        alive = Associate.objects.filter(is_deleted=False).count()
        self.stdout.write(self.style.SUCCESS(f"Done. Live associates remaining: {alive}"))

    def _rebuild_genealogy(self) -> None:
        gs = ConfigRepository.genealogy()
        old_mode, old_max = gs.leg_mode, gs.max_legs
        gs.leg_mode = GenealogySettings.LegMode.UNLIMITED
        gs.max_legs = 0
        gs.save(update_fields=["leg_mode", "max_legs", "updated_at"])
        try:
            GenealogyClosure.objects.all().delete()
            GenealogyNode.all_objects.update(parent=None)
            GenealogyNode.all_objects.all().delete()

            roots = list(
                Associate.objects.filter(sponsor__isnull=True, is_deleted=False).order_by("created_at")
            )
            for root in roots:
                GenealogyService.ensure_root(root)

            queue: deque[Associate] = deque(roots)
            seen = {r.pk for r in roots}
            while queue:
                parent = queue.popleft()
                children = list(
                    Associate.objects.filter(sponsor=parent, is_deleted=False).order_by("created_at")
                )
                for child in children:
                    if child.pk in seen:
                        continue
                    GenealogyService.attach_under_sponsor(child, parent)
                    seen.add(child.pk)
                    queue.append(child)

            for a in Associate.objects.filter(is_deleted=False):
                a.direct_count = a.directs.filter(is_deleted=False).count()
                a.direct_active_count = a.directs.filter(
                    status=Associate.Status.ACTIVE, is_deleted=False
                ).count()
                a.save(update_fields=["direct_count", "direct_active_count", "updated_at"])
        finally:
            gs.leg_mode = old_mode
            gs.max_legs = old_max
            gs.save(update_fields=["leg_mode", "max_legs", "updated_at"])
