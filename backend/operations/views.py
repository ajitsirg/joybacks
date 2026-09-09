from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from operations.models import DepositRequest, KYCSubmission, WithdrawalRequest
from operations.serializers import (
    DepositSerializer,
    KYCSerializer,
    ReviewActionSerializer,
    WithdrawalSerializer,
)
from operations.services import DepositService, KYCService, WithdrawalService


class StaffOrOwnerMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return qs
        if hasattr(user, "associate"):
            return qs.filter(associate=user.associate)
        return qs.none()


class KYCViewSet(StaffOrOwnerMixin, viewsets.ModelViewSet):
    queryset = KYCSubmission.objects.select_related("associate", "associate__user")
    serializer_class = KYCSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["status", "associate__status"]
    search_fields = ["associate__associate_id", "full_name", "pan", "aadhaar", "associate__mobile"]

    def get_queryset(self):
        qs = super().get_queryset().filter(associate__is_deleted=False)
        # Staff queue: hide soft-orphans; associates still see their own history.
        return qs

    def create(self, request, *args, **kwargs):
        """Upsert latest KYC instead of stacking duplicate pending rows."""
        if not hasattr(request.user, "associate"):
            return Response({"detail": "Associate profile required"}, status=403)
        assoc = request.user.associate
        latest = assoc.kyc_submissions.order_by("-created_at").first()
        if latest:
            ser = self.get_serializer(latest, data=request.data, partial=True)
            ser.is_valid(raise_exception=True)
            kyc = ser.save()
            kyc.status = KYCSubmission.Status.PENDING
            kyc.rejection_reason = ""
            kyc.reviewed_by = None
            kyc.reviewed_at = None
            kyc.save(
                update_fields=[
                    "status",
                    "rejection_reason",
                    "reviewed_by",
                    "reviewed_at",
                    "updated_at",
                ]
            )
            if assoc.kyc_verified:
                assoc.kyc_verified = False
                assoc.save(update_fields=["kyc_verified", "updated_at"])
            return Response(self.get_serializer(kyc).data)
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        kyc = ser.save(associate=assoc, status=KYCSubmission.Status.PENDING)
        headers = self.get_success_headers(ser.data)
        return Response(self.get_serializer(kyc).data, status=status.HTTP_201_CREATED, headers=headers)

    def _can_review(self, request, submission):
        user = request.user
        if user.is_staff or user.is_superuser:
            return True
        leader = getattr(user, "associate", None)
        return bool(leader and submission.associate.sponsor_id == leader.id)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        obj = self.get_object()
        if not self._can_review(request, obj):
            return Response({"detail": "Only the lead or staff can approve"}, status=403)
        try:
            obj = KYCService.approve(obj, actor=request.user)
        except (PermissionError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(KYCSerializer(obj, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        obj = self.get_object()
        if not self._can_review(request, obj):
            return Response({"detail": "Only the lead or staff can reject"}, status=403)
        ser = ReviewActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            obj = KYCService.reject(obj, actor=request.user, reason=ser.validated_data.get("reason", ""))
        except (PermissionError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(KYCSerializer(obj, context={"request": request}).data)


class DepositViewSet(StaffOrOwnerMixin, viewsets.ModelViewSet):
    queryset = DepositRequest.objects.select_related("associate", "associate__user")
    serializer_class = DepositSerializer
    filterset_fields = ["status", "wallet_type"]
    search_fields = ["associate__associate_id", "transaction_id"]

    def perform_create(self, serializer):
        if self.request.user.is_staff and self.request.data.get("associate_id"):
            from associates.models import Associate

            assoc = Associate.objects.get(associate_id=self.request.data["associate_id"])
            serializer.save(associate=assoc)
            return
        if not hasattr(self.request.user, "associate"):
            raise permissions.PermissionDenied("Associate profile required")
        serializer.save(associate=self.request.user.associate)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        try:
            obj = DepositService.approve(self.get_object(), actor=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(DepositSerializer(obj).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        ser = ReviewActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = DepositService.reject(self.get_object(), actor=request.user, reason=ser.validated_data.get("reason", ""))
        return Response(DepositSerializer(obj).data)


class WithdrawalViewSet(StaffOrOwnerMixin, viewsets.ModelViewSet):
    queryset = WithdrawalRequest.objects.select_related("associate", "associate__user")
    serializer_class = WithdrawalSerializer
    filterset_fields = ["status", "requires_maker_checker"]
    search_fields = ["associate__associate_id"]
    http_method_names = ["get", "post", "head", "options"]

    def create(self, request, *args, **kwargs):
        if not hasattr(request.user, "associate"):
            return Response({"detail": "Associate profile required"}, status=403)
        amount = request.data.get("amount")
        try:
            from decimal import Decimal

            obj = WithdrawalService.create(
                associate=request.user.associate,
                amount=Decimal(str(amount)),
                bank_detail=request.data.get("bank_detail", ""),
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(WithdrawalSerializer(obj).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        try:
            obj = WithdrawalService.approve(self.get_object(), actor=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(WithdrawalSerializer(obj).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        ser = ReviewActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            obj = WithdrawalService.reject(
                self.get_object(), actor=request.user, reason=ser.validated_data.get("reason", "")
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(WithdrawalSerializer(obj).data)
