from django.db.models import Q
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from associates.models import Associate
from audit.middleware import get_request_ip
from audit.services import write_audit
from genealogy.models import GenealogyClosure
from genealogy.serializers import GenealogyNodeSerializer
from genealogy.services import GenealogyService


def _viewer_associate(user):
    return getattr(user, "associate", None)


def _is_staff(user) -> bool:
    return bool(user and (user.is_staff or user.is_superuser))


def _can_view(user, target: Associate) -> bool:
    """Staff: anyone. Associate: self or own downline only."""
    if _is_staff(user):
        return True
    me = _viewer_associate(user)
    if not me:
        return False
    if me.id == target.id:
        return True
    return GenealogyClosure.objects.filter(ancestor=me, descendant=target, depth__gt=0).exists()


class GenealogyTreeView(APIView):
    """Expandable tree — associates only see their own downline; staff see full company."""

    def get(self, request):
        associate_id = request.query_params.get("associate_id")
        me = _viewer_associate(request.user)
        staff = _is_staff(request.user)

        # Default root: associate → self; staff → company top root
        if not associate_id:
            if me and not staff:
                associate_id = me.associate_id
            elif staff:
                roots = GenealogyService.company_roots()
                if not roots:
                    return Response({"detail": "No company root found"}, status=404)
                associate_id = roots[0].associate_id
            else:
                return Response({"detail": "associate_id is required"}, status=400)

        try:
            associate = Associate.objects.select_related("user", "genealogy_node").get(
                associate_id__iexact=associate_id
            )
        except Associate.DoesNotExist:
            return Response({"detail": "Associate not found"}, status=404)

        if not _can_view(request.user, associate):
            return Response(
                {"detail": "You can only view your own downline associate tree."},
                status=403,
            )

        children = GenealogyService.tree_children(associate)
        return Response(
            {
                "node": GenealogyNodeSerializer(associate).data,
                "children": GenealogyNodeSerializer(children, many=True).data,
                "scoped_to": me.associate_id if me and not staff else None,
                "is_company_root": associate.sponsor_id is None,
            }
        )


class GenealogyRootsView(APIView):
    """Staff only — company tree root(s) for full-network view."""

    def get(self, request):
        if not _is_staff(request.user):
            return Response({"detail": "Staff only"}, status=403)
        roots = GenealogyService.company_roots()
        return Response(
            {
                "count": len(roots),
                "results": GenealogyNodeSerializer(roots, many=True).data,
            }
        )


class GenealogySearchView(APIView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if len(q) < 2:
            return Response([])

        qs = Associate.objects.select_related("user").filter(
            Q(associate_id__icontains=q)
            | Q(referral_code__icontains=q)
            | Q(user__email__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
        )

        if not _is_staff(request.user):
            me = _viewer_associate(request.user)
            if not me:
                return Response([])
            downline_ids = GenealogyClosure.objects.filter(ancestor=me).values_list("descendant_id", flat=True)
            qs = qs.filter(id__in=downline_ids)

        return Response(GenealogyNodeSerializer(qs[:20], many=True).data)


class UplineView(APIView):
    def get(self, request, associate_id: str):
        # Associates may only see their own downline — never upline / peers.
        if not _is_staff(request.user):
            return Response(
                {
                    "detail": "Associates can only view their downline team.",
                    "results": [],
                },
                status=403,
            )
        try:
            associate = Associate.objects.get(associate_id__iexact=associate_id)
        except Associate.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)
        levels = request.query_params.get("levels")
        max_levels = int(levels) if levels else None
        links = GenealogyService.upline(associate, max_levels=max_levels)
        data = [
            {
                "depth": link.depth,
                "associate": GenealogyNodeSerializer(link.ancestor).data,
            }
            for link in links
        ]
        return Response(data)


class ShiftAssociateView(APIView):
    """
    Staff / super-admin: place any associate under any other associate.
    Moves the entire downline (leg) with them.
    """

    def post(self, request):
        user = request.user
        if not (getattr(user, "is_superuser", False) or getattr(user, "is_staff", False)):
            return Response(
                {"detail": "Only admin staff can shift associates in the tree."},
                status=403,
            )

        associate_id = str(request.data.get("associate_id") or "").strip().upper()
        new_sponsor_id = str(
            request.data.get("new_sponsor_id") or request.data.get("under_associate_id") or ""
        ).strip().upper()
        if not associate_id or not new_sponsor_id:
            return Response(
                {"detail": "associate_id and new_sponsor_id are required"},
                status=400,
            )

        try:
            associate = Associate.objects.select_related("sponsor", "user").get(
                associate_id__iexact=associate_id, is_deleted=False
            )
        except Associate.DoesNotExist:
            return Response({"detail": f"Associate {associate_id} not found"}, status=404)

        try:
            new_sponsor = Associate.objects.select_related("user").get(
                associate_id__iexact=new_sponsor_id, is_deleted=False
            )
        except Associate.DoesNotExist:
            return Response({"detail": f"New sponsor {new_sponsor_id} not found"}, status=404)

        try:
            result = GenealogyService.shift_subtree(associate, new_sponsor, force=True)
        except ValidationError as exc:
            detail = exc.detail
            if isinstance(detail, dict):
                msg = detail.get("detail") or next(iter(detail.values()), str(detail))
                if isinstance(msg, (list, tuple)):
                    msg = msg[0]
            else:
                msg = str(detail)
            return Response({"detail": str(msg)}, status=400)

        write_audit(
            actor=request.user,
            action="genealogy.shift",
            module="genealogy",
            object_type="Associate",
            object_id=str(associate.id),
            ip_address=get_request_ip(),
            metadata=result,
        )
        return Response({"detail": "Associate shifted successfully.", **result})
