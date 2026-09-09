"""Soft-remove Ganpati dummy army (JOY9998887771 / JOYDUM* / JOYIND*) without deleting real associates."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from associates.models import Associate
from genealogy.services import GenealogyService

User = get_user_model()

COMPANY_ROOT = "JOYSIDDHI01"


def _is_dummy(assoc: Associate) -> bool:
    aid = (assoc.associate_id or "").upper()
    email = (getattr(assoc.user, "email", "") or "").lower()
    name = ((assoc.user.get_full_name() if assoc.user_id else "") or "").lower()
    if aid in {"JOY9998887771", "JOY9887700001"}:
        return True
    if aid.startswith("JOYDUM") or aid.startswith("JOYIND"):
        return True
    if email.endswith("@joyclub.dummy") or email == "dummy.army@joyclubs.in":
        return True
    if name.startswith("direct") and name.endswith("member"):
        return True
    if name.startswith("indirect") and name.endswith("member"):
        return True
    if "dummy army" in name:
        return True
    return False


class Command(BaseCommand):
    help = "Soft-delete dummy army associates and reattach any real members under company root"

    def handle(self, *args, **options):
        root = Associate.objects.filter(associate_id__iexact=COMPANY_ROOT, is_deleted=False).first()
        if not root:
            self.stderr.write(f"Company root {COMPANY_ROOT} missing")
            return

        candidates = list(
            Associate.all_objects.filter(is_deleted=False)
            .filter(
                Q(associate_id__iexact="JOY9998887771")
                | Q(associate_id__iexact="JOY9887700001")
                | Q(associate_id__startswith="JOYDUM")
                | Q(associate_id__startswith="JOYIND")
                | Q(user__email__iendswith="@joyclub.dummy")
                | Q(user__email__iexact="dummy.army@joyclubs.in")
            )
            .select_related("user", "genealogy_node")
        )
        demos = [a for a in candidates if _is_dummy(a)]
        demo_ids = {a.id for a in demos}
        if not demos:
            self.stdout.write("No dummy-army associates found")
            return

        self.stdout.write(f"Removing {len(demos)} dummy associates…")

        # Real associates currently sponsored by a dummy → move under company root
        orphans = list(
            Associate.objects.filter(sponsor_id__in=demo_ids, is_deleted=False)
            .exclude(id__in=demo_ids)
            .select_related("user")
        )

        with transaction.atomic():
            for real in orphans:
                self.stdout.write(
                    f"  reparent {real.associate_id} "
                    f"(was under {real.sponsor_associate_id}) → {root.associate_id}"
                )
                try:
                    GenealogyService.shift_subtree(real, root, force=True)
                except Exception as exc:  # noqa: BLE001
                    self.stderr.write(f"  shift failed for {real.associate_id}: {exc}")
                    real.sponsor = root
                    real.sponsor_associate_id = root.associate_id
                    real.save(update_fields=["sponsor", "sponsor_associate_id", "updated_at"])

            ordered = sorted(
                demos,
                key=lambda a: getattr(getattr(a, "genealogy_node", None), "depth", 0),
                reverse=True,
            )
            for assoc in ordered:
                GenealogyService.hard_detach(assoc)
                Associate.all_objects.filter(sponsor=assoc).exclude(id__in=demo_ids).update(
                    sponsor=root,
                    sponsor_associate_id=root.associate_id,
                )
                assoc.is_deleted = True
                assoc.deleted_at = timezone.now()
                assoc.status = Associate.Status.INACTIVE
                assoc.save(update_fields=["is_deleted", "deleted_at", "status", "updated_at"])
                u = assoc.user
                if u and not u.is_staff and not u.is_superuser:
                    u.is_active = False
                    u.save(update_fields=["is_active"])
                self.stdout.write(f"  removed {assoc.associate_id}")

            GenealogyService._refresh_direct_counts(root)

        alive_dummy = Associate.objects.filter(
            Q(associate_id__startswith="JOYDUM")
            | Q(associate_id__startswith="JOYIND")
            | Q(associate_id__iexact="JOY9998887771")
        ).count()
        self.stdout.write(self.style.SUCCESS(f"Done. Remaining alive dummy IDs: {alive_dummy}"))
        self.stdout.write(f"Reparented real associates: {len(orphans)}")
