from rest_framework import generics, permissions

from commissions.models import AdminCharge, CommissionEntry, CommissionRun
from commissions.serializers import AdminChargeSerializer, CommissionEntrySerializer, CommissionRunSerializer


class CommissionRunListView(generics.ListAPIView):
    queryset = CommissionRun.objects.prefetch_related("entries").all()
    serializer_class = CommissionRunSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ["run_type", "status"]


class CommissionEntryListView(generics.ListAPIView):
    serializer_class = CommissionEntrySerializer
    filterset_fields = [
        "level",
        "wallet_type",
        "beneficiary__associate_id",
        "source_associate__associate_id",
        "status",
        "reference",
        "month_index",
    ]

    def get_queryset(self):
        qs = CommissionEntry.objects.select_related("beneficiary", "source_associate", "run")
        if not self.request.query_params.get("status"):
            qs = qs.exclude(status=CommissionEntry.Status.VOIDED)
        user = self.request.user
        if user.is_staff or user.is_superuser:
            scoped = qs
        else:
            me = getattr(user, "associate", None)
            if not me:
                return qs.none()
            from genealogy.models import GenealogyClosure

            ids = GenealogyClosure.objects.filter(ancestor=me).values_list("descendant_id", flat=True)
            scoped = qs.filter(beneficiary_id__in=ids)

        min_level = self.request.query_params.get("min_level")
        if min_level is not None and str(min_level).strip() != "":
            scoped = scoped.filter(level__gte=int(min_level))
        max_level = self.request.query_params.get("max_level")
        if max_level is not None and str(max_level).strip() != "":
            scoped = scoped.filter(level__lte=int(max_level))
        if self.request.query_params.get("roi_on_roi") in ("1", "true", "yes"):
            scoped = scoped.filter(level__gte=1)
        if self.request.query_params.get("base_roi_only") in ("1", "true", "yes"):
            scoped = scoped.filter(level=0)
        elif (self.request.query_params.get("wallet_type") or "").lower() == "roi":
            # Investor's own month ROI (level 0 / ₹2,200) is never shown.
            scoped = scoped.filter(level__gte=1)
        return scoped


class AdminChargeListView(generics.ListAPIView):
    """Staff / finance only. Associates must never see admin-charge rows."""

    serializer_class = AdminChargeSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ["kind", "wallet_type", "associate__associate_id"]
    search_fields = ["associate__associate_id", "reference", "narration"]

    def get_queryset(self):
        return AdminCharge.objects.select_related("associate", "associate__user").all()
