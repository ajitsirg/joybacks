from __future__ import annotations

from collections import deque

from django.db import transaction
from rest_framework.exceptions import ValidationError

from associates.models import Associate
from configuration.repository import ConfigRepository
from genealogy.models import GenealogyClosure, GenealogyNode


class GenealogyService:
    @staticmethod
    @transaction.atomic
    def attach_under_sponsor(
        associate: Associate,
        sponsor: Associate,
        *,
        force: bool = False,
    ) -> GenealogyNode:
        # Capacity: directs already under sponsor (associate may not be linked yet)
        genealogy = ConfigRepository.genealogy()
        max_legs = genealogy.effective_max_legs()
        if not force and max_legs > 0:
            current = sponsor.directs.filter(is_deleted=False).exclude(pk=associate.pk).count()
            if current >= max_legs:
                raise ValidationError(
                    {
                        "detail": (
                            f"Sponsor leg capacity reached ({current}/{max_legs}). "
                            "Admin can change this in Genealogy settings."
                        )
                    }
                )

        parent_node = getattr(sponsor, "genealogy_node", None)
        if parent_node is None:
            parent_node = GenealogyService.ensure_root(sponsor)

        max_depth = int(genealogy.max_depth or 0)
        next_depth = parent_node.depth + 1
        if not force and max_depth > 0 and next_depth > max_depth:
            raise ValidationError(
                {
                    "detail": (
                        f"Tree depth limit reached ({next_depth}/{max_depth}). "
                        "Admin can raise this in Genealogy settings (max depth)."
                    )
                }
            )

        leg_index = associate.placement_leg or (parent_node.children.count() + 1)
        if not force and max_legs > 0 and leg_index > max_legs:
            raise ValidationError(
                {"detail": f"Leg index {leg_index} exceeds admin max legs ({max_legs})."}
            )
        path = f"{parent_node.path}{associate.id}/"
        node = GenealogyNode.objects.create(
            associate=associate,
            parent=parent_node,
            path=path,
            depth=next_depth,
            leg_index=leg_index,
        )

        # Self link
        GenealogyClosure.objects.create(ancestor=associate, descendant=associate, depth=0)
        # Copy ancestor chain
        for link in GenealogyClosure.objects.filter(descendant=sponsor):
            GenealogyClosure.objects.create(
                ancestor=link.ancestor,
                descendant=associate,
                depth=link.depth + 1,
            )
        return node

    @staticmethod
    @transaction.atomic
    def hard_detach(associate: Associate) -> None:
        """Remove genealogy node/closure for one associate (hard delete; children must be detached first)."""
        GenealogyClosure.objects.filter(descendant=associate).delete()
        GenealogyClosure.objects.filter(ancestor=associate).delete()
        # Hard-remove node so associate FK / parent PROTECT cannot block purge
        GenealogyNode.all_objects.filter(associate=associate).delete(force=True)

    @staticmethod
    @transaction.atomic
    def rebuild_under_sponsor(associate: Associate, sponsor: Associate) -> GenealogyNode:
        GenealogyService.hard_detach(associate)
        return GenealogyService.attach_under_sponsor(associate, sponsor)

    @staticmethod
    @transaction.atomic
    def rebuild_tree(ordered_pairs: list[tuple[Associate, Associate]]) -> None:
        """
        Rebuild genealogy for a list of (associate, sponsor) pairs.
        Detach deepest first, then attach in given order (parents before children).
        """
        # Detach in reverse so children are removed before parents (PROTECT)
        for associate, _sponsor in reversed(ordered_pairs):
            GenealogyService.hard_detach(associate)
        for associate, sponsor in ordered_pairs:
            GenealogyService.attach_under_sponsor(associate, sponsor)

    @staticmethod
    def ensure_root(associate: Associate) -> GenealogyNode:
        node, _ = GenealogyNode.objects.get_or_create(
            associate=associate,
            defaults={
                "parent": None,
                "path": f"/{associate.id}/",
                "depth": 0,
                "leg_index": 0,
            },
        )
        GenealogyClosure.objects.get_or_create(
            ancestor=associate,
            descendant=associate,
            defaults={"depth": 0},
        )
        return node

    @staticmethod
    def tree_children(associate: Associate) -> list[Associate]:
        node = getattr(associate, "genealogy_node", None)
        if node:
            kids = [
                child.associate
                for child in node.children.select_related("associate", "associate__user").order_by(
                    "leg_index"
                )
                if child.associate and not child.associate.is_deleted
            ]
            if kids:
                return kids
        # Fallback: sponsor FK children (covers nodes missing from genealogy path)
        return list(
            Associate.objects.filter(sponsor=associate, is_deleted=False)
            .select_related("user")
            .order_by("created_at")
        )

    @staticmethod
    def company_roots() -> list[Associate]:
        """Top of company tree — associates with no sponsor."""
        return list(
            Associate.objects.filter(sponsor__isnull=True, is_deleted=False)
            .select_related("user", "genealogy_node")
            .order_by("created_at")
        )

    @staticmethod
    def upline(associate: Associate, max_levels: int | None = None):
        qs = GenealogyClosure.objects.filter(descendant=associate, depth__gt=0).select_related(
            "ancestor", "ancestor__user"
        ).order_by("depth")
        if max_levels:
            qs = qs.filter(depth__lte=max_levels)
        return qs

    @staticmethod
    def downline(associate: Associate, max_depth: int | None = None):
        qs = GenealogyClosure.objects.filter(ancestor=associate, depth__gt=0).select_related(
            "descendant", "descendant__user"
        ).order_by("depth")
        if max_depth:
            qs = qs.filter(depth__lte=max_depth)
        return qs

    @staticmethod
    def _refresh_direct_counts(sponsor: Associate | None) -> None:
        if not sponsor:
            return
        sponsor.direct_count = sponsor.directs.filter(is_deleted=False).count()
        sponsor.direct_active_count = sponsor.directs.filter(
            is_deleted=False, status=Associate.Status.ACTIVE
        ).count()
        sponsor.save(update_fields=["direct_count", "direct_active_count", "updated_at"])
        if hasattr(sponsor, "sync_performance_level"):
            sponsor.sync_performance_level(save=True)

    @staticmethod
    @transaction.atomic
    def shift_subtree(
        associate: Associate,
        new_sponsor: Associate,
        *,
        force: bool = True,
    ) -> dict:
        """
        Super-admin power: place `associate` under `new_sponsor` and move the entire
        downline (leg) with them. Updates sponsor FK on the moved root only; rebuilds
        genealogy nodes/closure for the whole subtree.
        """
        if associate.is_deleted or new_sponsor.is_deleted:
            raise ValidationError({"detail": "Cannot shift deleted associates."})
        if associate.pk == new_sponsor.pk:
            raise ValidationError({"detail": "Cannot place an associate under themselves."})

        # Cycle: new sponsor cannot be inside the mover's downline
        if GenealogyClosure.objects.filter(
            ancestor=associate, descendant=new_sponsor, depth__gt=0
        ).exists():
            raise ValidationError(
                {
                    "detail": (
                        f"{new_sponsor.associate_id} is already under {associate.associate_id}. "
                        "Moving there would create a cycle."
                    )
                }
            )

        old_sponsor = associate.sponsor

        # Collect entire leg: closure descendants + sponsor-FK tree (pending joiners too)
        subtree_ids: set = {associate.pk}
        for desc_id in GenealogyClosure.objects.filter(ancestor=associate, depth__gt=0).values_list(
            "descendant_id", flat=True
        ):
            subtree_ids.add(desc_id)

        queue: deque = deque([associate.pk])
        while queue:
            parent_id = queue.popleft()
            for child_id in Associate.objects.filter(
                sponsor_id=parent_id, is_deleted=False
            ).values_list("id", flat=True):
                if child_id not in subtree_ids:
                    subtree_ids.add(child_id)
                    queue.append(child_id)

        # Re-point only the moved root (downline keeps their own sponsors)
        associate.sponsor = new_sponsor
        associate.sponsor_associate_id = new_sponsor.associate_id
        associate.placement_leg = 0  # auto under new sponsor
        associate.save(
            update_fields=["sponsor", "sponsor_associate_id", "placement_leg", "updated_at"]
        )

        # Build attach order: mover first, then BFS by sponsor FK within subtree
        ordered: list[tuple[Associate, Associate]] = [(associate, new_sponsor)]
        bfs: deque[Associate] = deque([associate])
        seen_attach = {associate.pk}
        while bfs:
            parent = bfs.popleft()
            kids = (
                Associate.objects.filter(sponsor=parent, is_deleted=False, id__in=subtree_ids)
                .select_related("user")
                .order_by("created_at")
            )
            for kid in kids:
                if kid.pk in seen_attach:
                    continue
                seen_attach.add(kid.pk)
                ordered.append((kid, parent))
                bfs.append(kid)

        # Detach deepest-first (PROTECT on parent FK)
        nodes = list(
            GenealogyNode.objects.filter(associate_id__in=subtree_ids)
            .select_related("associate")
            .order_by("-depth")
        )
        for node in nodes:
            GenealogyService.hard_detach(node.associate)

        # Ensure new sponsor has a node
        if not GenealogyNode.objects.filter(associate=new_sponsor).exists():
            GenealogyService.ensure_root(new_sponsor)

        for person, sponsor in ordered:
            # Skip attach for people who were never on the tree and are still pending?
            # Always attach so the shifted leg is visible in genealogy.
            GenealogyService.attach_under_sponsor(person, sponsor, force=force)

        GenealogyService._refresh_direct_counts(old_sponsor)
        GenealogyService._refresh_direct_counts(new_sponsor)

        return {
            "associate_id": associate.associate_id,
            "old_sponsor_id": old_sponsor.associate_id if old_sponsor else None,
            "new_sponsor_id": new_sponsor.associate_id,
            "moved_count": len(subtree_ids),
            "subtree_ids": [
                a.associate_id
                for a in Associate.objects.filter(id__in=subtree_ids).order_by("associate_id")
            ],
        }
