from decimal import Decimal

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.services import AuthService
from associates.models import Associate
from associates.serializers import (
    AssociateRegisterSerializer,
    AssociateSerializer,
    AssociateUpdateSerializer,
    JoinPreviewSerializer,
    LeaderReviewSerializer,
    PendingJoinSerializer,
)
from associates.services import (
    AssociateService,
    can_edit_associate,
    can_view_associate_details,
    can_view_associate_profile,
)
from audit.middleware import get_request_ip
from genealogy.models import GenealogyClosure, GenealogyNode


class AssociateViewSet(viewsets.ModelViewSet):
    queryset = Associate.objects.select_related("user", "sponsor", "genealogy_node").prefetch_related(
        "kyc_submissions", "wallets"
    )
    serializer_class = AssociateSerializer
    http_method_names = ["get", "head", "options", "patch"]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = "associate_id"
    lookup_url_kwarg = "associate_id"
    lookup_value_regex = r"[Jj][A-Za-z0-9]+"
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        "status",
        "kyc_verified",
        "sponsor_associate_id",
        "card_tier",
        "flag_color",
        "earning_level",
        "performance_level",
    ]
    search_fields = ["associate_id", "referral_code", "user__email", "user__first_name", "mobile", "lead_reference"]
    ordering_fields = [
        "created_at",
        "total_business",
        "direct_count",
        "join_amount",
        "earning_level",
        "performance_level",
    ]

    def get_permissions(self):
        if self.action in ("list", "retrieve", "partial_update", "level_summary"):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    def get_serializer_class(self):
        if self.action == "partial_update":
            return AssociateUpdateSerializer
        return AssociateSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        me = getattr(user, "associate", None)
        scope = (self.request.query_params.get("scope") or "").strip().lower()

        # Absolute tree depth from company root (GenealogyNode.depth)
        qs = qs.annotate(
            tree_level=Subquery(
                GenealogyNode.objects.filter(associate_id=OuterRef("pk")).values("depth")[:1],
                output_field=IntegerField(),
            )
        )

        # Relative level under the logged-in associate (1 = direct, 2 = next, …)
        if me:
            qs = qs.annotate(
                leg_level=Subquery(
                    GenealogyClosure.objects.filter(
                        ancestor=me, descendant_id=OuterRef("pk")
                    ).values("depth")[:1],
                    output_field=IntegerField(),
                )
            )

        # My Associates: under-leg only (associates + staff who have an associate profile)
        if scope == "my":
            if not me:
                return qs.none()
            downline_ids = GenealogyClosure.objects.filter(ancestor=me, depth__gt=0).values_list(
                "descendant_id", flat=True
            )
            qs = qs.filter(Q(id__in=downline_ids) | Q(sponsor=me)).exclude(pk=me.pk)
        elif user.is_staff or user.is_superuser:
            pass  # full tree
        elif not me:
            return qs.none()
        else:
            # Associate default list: own under-leg only
            downline_ids = GenealogyClosure.objects.filter(ancestor=me, depth__gt=0).values_list(
                "descendant_id", flat=True
            )
            qs = qs.filter(Q(id__in=downline_ids) | Q(sponsor=me)).exclude(pk=me.pk)

        # Filter by absolute tree depth or relative under-leg depth
        tree_raw = (self.request.query_params.get("tree_level") or "").strip()
        if tree_raw != "":
            try:
                qs = qs.filter(tree_level=int(tree_raw))
            except (TypeError, ValueError):
                qs = qs.none()
        leg_raw = (self.request.query_params.get("leg_level") or "").strip()
        if leg_raw != "":
            try:
                qs = qs.filter(leg_level=int(leg_raw))
            except (TypeError, ValueError):
                qs = qs.none()
        return qs

    def get_object(self):
        lookup = self.kwargs.get(self.lookup_url_kwarg) or self.kwargs.get("pk")
        try:
            obj = Associate.objects.select_related("user", "sponsor").prefetch_related(
                "kyc_submissions"
            ).get(associate_id__iexact=str(lookup).strip(), is_deleted=False)
        except Associate.DoesNotExist as exc:
            raise NotFound("Associate not found") from exc

        user = self.request.user
        if self.action == "partial_update":
            if not can_edit_associate(user, obj):
                raise PermissionDenied("You cannot update this associate")
            return obj

        # Tree / team profile: self, staff, or own downline. KYC still gated in serializer.
        if can_view_associate_profile(user, obj):
            return obj
        raise NotFound("Associate not found")

    def partial_update(self, request, *args, **kwargs):
        associate = self.get_object()
        serializer = AssociateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        files = {}
        for key in (
            "profile_photo",
            "aadhaar_document",
            "aadhaar_front",
            "aadhaar_back",
            "pan_document",
            "bank_document",
        ):
            if key in data:
                files[key] = data.pop(key)
            elif key in request.FILES:
                files[key] = request.FILES.get(key)
        if files.get("aadhaar_front") and not files.get("aadhaar_document"):
            files["aadhaar_document"] = files["aadhaar_front"]
        # Boolean fields may arrive as strings via multipart
        for key in ("can_view_admin_history", "can_view_reward_achievers", "can_fund_transfer"):
            if key in request.data and key not in data:
                raw = request.data.get(key)
                if isinstance(raw, str):
                    data[key] = raw.strip().lower() in ("1", "true", "yes", "on")
                else:
                    data[key] = bool(raw)
        try:
            associate = AssociateService.update_details(
                associate,
                actor=request.user,
                data=data,
                files=files,
                ip=get_request_ip(),
            )
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(AssociateSerializer(associate, context={"request": request}).data)

    @action(detail=False, methods=["get"], url_path="level-summary")
    def level_summary(self, request):
        """Counts per network (tree/leg), reward, or performance level."""
        kind = str(request.query_params.get("kind") or "tree").strip().lower()
        me = getattr(request.user, "associate", None)
        is_staff = request.user.is_staff or request.user.is_superuser

        if kind in ("tree", "network", "leg"):
            use_leg = kind == "leg" or (not is_staff and me is not None)
            if use_leg:
                if not me:
                    return Response({"kind": "leg", "results": []})
                downline_ids = GenealogyClosure.objects.filter(
                    ancestor=me, depth__gt=0
                ).values_list("descendant_id", flat=True)
                qs = (
                    Associate.objects.filter(is_deleted=False)
                    .filter(Q(id__in=downline_ids) | Q(sponsor=me))
                    .exclude(pk=me.pk)
                    .annotate(
                        leg_level=Subquery(
                            GenealogyClosure.objects.filter(
                                ancestor=me, descendant_id=OuterRef("pk")
                            ).values("depth")[:1],
                            output_field=IntegerField(),
                        )
                    )
                )
                field = "leg_level"
                out_kind = "leg"
            else:
                qs = (
                    Associate.objects.filter(is_deleted=False)
                    .annotate(
                        tree_level=Subquery(
                            GenealogyNode.objects.filter(associate_id=OuterRef("pk")).values(
                                "depth"
                            )[:1],
                            output_field=IntegerField(),
                        )
                    )
                )
                field = "tree_level"
                out_kind = "tree"

            rows = (
                qs.exclude(**{f"{field}__isnull": True})
                .values(field)
                .annotate(count=Count("id"))
                .order_by(field)
            )
            results = []
            for row in rows:
                level = int(row[field] or 0)
                if row[field] is None:
                    continue
                # Network "Level 1" = first under-leg / depth 1 (skip root depth 0 for tree cards)
                results.append(
                    {
                        "level": level,
                        "name": "Root" if level == 0 else f"Level {level}",
                        "count": int(row["count"] or 0),
                    }
                )
            return Response({"kind": out_kind, "results": results})

        qs = self.filter_queryset(self.get_queryset())
        if kind in ("performance", "sp"):
            field, name_field = "performance_level", "performance_level_name"
            out_kind = "performance"
        else:
            field, name_field = "earning_level", "earning_level_name"
            out_kind = "reward"

        rows = qs.values(field, name_field).annotate(count=Count("id")).order_by(field)
        results = [
            {
                "level": int(row[field] or 0),
                "name": row[name_field] or (f"Level {row[field]}" if row[field] else "No level"),
                "count": int(row["count"] or 0),
            }
            for row in rows
        ]
        return Response({"kind": out_kind, "results": results})


class RegisterAssociateView(APIView):
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(request=AssociateRegisterSerializer, responses=AssociateSerializer)
    def post(self, request):
        from rest_framework.exceptions import ValidationError

        from associates.validators import validate_sponsor

        serializer = AssociateRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        mobile = data["mobile"]  # already normalized by validate_mobile

        # Validate lead before consuming OTP so a bad lead does not burn the code.
        try:
            validate_sponsor(str(data.get("lead_reference") or ""))
        except ValidationError as exc:
            detail = exc.detail
            if isinstance(detail, dict):
                msg = next(iter(detail.values()))
                if isinstance(msg, (list, tuple)):
                    msg = msg[0] if msg else "Invalid lead reference"
                return Response({"detail": str(msg), **{k: v for k, v in detail.items()}}, status=400)
            return Response({"detail": str(detail)}, status=400)

        from configuration.repository import ConfigRepository

        company = ConfigRepository.company()
        require_otp = bool(company.require_join_otp)
        if require_otp:
            otp_ok = AuthService.verify_otp(
                phone_or_email=mobile,
                purpose="register",
                code=data.get("otp") or "",
            )
            if not otp_ok:
                return Response({"detail": "Invalid or expired OTP"}, status=400)
        try:
            associate = AssociateService.register(
                email=data.get("email", ""),
                password=data["password"],
                first_name=data["first_name"],
                last_name=data.get("last_name", ""),
                mobile=mobile,
                lead_reference=data["lead_reference"],
                join_amount=Decimal(data.get("join_amount") or 0),
                otp_verified=True,
                ip=get_request_ip(),
                pan=data.get("pan", ""),
                aadhaar=data.get("aadhaar", ""),
                bank_name=data.get("bank_name", ""),
                account_number=data.get("account_number", ""),
                ifsc=data.get("ifsc", ""),
                upi_id=data.get("upi_id", ""),
                profile_photo=data.get("profile_photo"),
                aadhaar_document=data.get("aadhaar_document") or data.get("aadhaar_front"),
                aadhaar_back=data.get("aadhaar_back"),
                pan_document=data.get("pan_document"),
                bank_document=data.get("bank_document"),
            )
        except ValidationError as exc:
            detail = exc.detail
            if isinstance(detail, dict):
                msg = next(iter(detail.values()))
                if isinstance(msg, (list, tuple)):
                    msg = msg[0] if msg else "Validation failed"
                return Response({"detail": str(msg)}, status=400)
            return Response({"detail": str(detail)}, status=400)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=400)
        payload = AssociateSerializer(associate, context={"request": request}).data
        st = str(associate.status).lower()
        # Inactive = approved, can open dashboard; Active = invested ≥ ₹2.2L
        can_enter = st in {"active", "inactive"}
        payload["auto_activated"] = can_enter
        if st == "active":
            payload["detail"] = "Welcome! Your account is Active."
        elif st == "inactive":
            payload["detail"] = (
                "Welcome! Invest at least ₹2,20,000 to become Active."
            )
        else:
            payload["detail"] = "Wait for your team lead approval"
        return Response(payload, status=status.HTTP_201_CREATED)


class RequestRegisterOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from core.validators import validate_mobile

        try:
            mobile = validate_mobile(request.data.get("mobile", ""))
        except DjangoValidationError as exc:
            msg = exc.messages[0] if exc.messages else "Valid mobile required"
            return Response({"detail": msg, "mobile": [msg]}, status=400)
        code = AuthService.create_otp(phone_or_email=mobile, purpose="register")
        payload = {"detail": "OTP sent to mobile"}
        from django.conf import settings

        if settings.DEBUG:
            payload["debug_otp"] = code
        return Response(payload)


class JoinPreviewView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = JoinPreviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(JoinPreviewSerializer(ser.validated_data).data)


class ActivateAssociateView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, associate_id: str):
        try:
            associate = Associate.objects.get(associate_id__iexact=associate_id)
        except Associate.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)
        associate = AssociateService.activate(associate, actor=request.user)
        return Response(AssociateSerializer(associate).data)


def _team_approvals_enabled() -> bool:
    from configuration.repository import ConfigRepository

    return bool(ConfigRepository.company().require_leader_approval)


class PendingJoinsView(APIView):
    """Leaders see join requests under them; staff see all pending."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not _team_approvals_enabled():
            return Response(
                {
                    "count": 0,
                    "results": [],
                    "detail": "Team Approvals is disabled in company settings.",
                    "enabled": False,
                }
            )
        qs = Associate.objects.select_related("user").prefetch_related("kyc_submissions").filter(
            status=Associate.Status.PENDING, is_deleted=False
        )
        user = request.user
        if not (user.is_staff or user.is_superuser):
            leader = getattr(user, "associate", None)
            if not leader:
                return Response({"detail": "Associate profile required"}, status=403)
            qs = qs.filter(sponsor=leader)
        data = PendingJoinSerializer(qs.order_by("-created_at"), many=True, context={"request": request}).data
        return Response({"count": len(data), "results": data, "enabled": True})


class LeaderApproveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, associate_id: str):
        if not _team_approvals_enabled():
            return Response(
                {"detail": "Team Approvals is disabled in company settings."},
                status=400,
            )
        try:
            associate = Associate.objects.select_related("sponsor", "user").get(associate_id__iexact=associate_id)
        except Associate.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)
        try:
            associate = AssociateService.leader_approve(associate, actor=request.user)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(AssociateSerializer(associate).data)


class LeaderRejectView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, associate_id: str):
        if not _team_approvals_enabled():
            return Response(
                {"detail": "Team Approvals is disabled in company settings."},
                status=400,
            )
        ser = LeaderReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            associate = Associate.objects.select_related("sponsor", "user").get(associate_id__iexact=associate_id)
        except Associate.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)
        try:
            associate = AssociateService.leader_reject(
                associate, actor=request.user, reason=ser.validated_data.get("reason", "")
            )
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(AssociateSerializer(associate).data)


class RewardProgressView(APIView):
    """Live 3-leg Reward Achievement progress for the signed-in associate."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        me = getattr(request.user, "associate", None)
        if not me:
            return Response({"detail": "Associate profile required"}, status=403)
        me.sync_earning_level(save=True)
        from associates.rewards import progress_api_dict

        return Response(progress_api_dict(me))


class RewardLegsAssignView(APIView):
    """Pin Leg 1/2/3 to first-line members, or return to automatic top-3."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        me = getattr(request.user, "associate", None)
        if not me:
            return Response({"detail": "Associate profile required"}, status=403)
        from associates.rewards import progress_api_dict, set_reward_legs

        auto = bool(request.data.get("auto"))
        raw = request.data.get("legs") or [
            request.data.get("leg1"),
            request.data.get("leg2"),
            request.data.get("leg3"),
        ]
        ids = [str(x).strip() for x in raw if x]
        try:
            set_reward_legs(me, performer_ids=None if auto else ids, auto=auto)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        me.sync_earning_level(save=True)
        return Response(progress_api_dict(me))
