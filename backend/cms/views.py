from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from cms.models import (
    HelpTicket,
    KnowledgeItem,
    LandingBenefit,
    LandingGalleryItem,
    LandingPageSettings,
    NewsItem,
    QRWalletSetting,
)
from cms.serializers import (
    HelpTicketSerializer,
    KnowledgeItemSerializer,
    LandingBenefitSerializer,
    LandingGalleryItemSerializer,
    LandingPageSettingsSerializer,
    NewsItemSerializer,
    QRWalletSettingSerializer,
)


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_staff


class NewsViewSet(viewsets.ModelViewSet):
    queryset = NewsItem.objects.all()
    serializer_class = NewsItemSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["is_published"]
    search_fields = ["title", "body"]


class HelpTicketViewSet(viewsets.ModelViewSet):
    queryset = HelpTicket.objects.all()
    serializer_class = HelpTicketSerializer
    filterset_fields = ["status"]
    search_fields = ["subject", "email", "associate_id"]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]


class QRWalletViewSet(viewsets.ModelViewSet):
    queryset = QRWalletSetting.objects.all()
    serializer_class = QRWalletSettingSerializer
    permission_classes = [IsAdminOrReadOnly]


class LandingPageView(APIView):
    """Public landing page partner section (home bottom)."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        settings_obj = LandingPageSettings.current()
        if not settings_obj.is_active:
            return Response({"active": False})
        benefits = LandingBenefit.objects.filter(is_active=True).order_by("sort_order", "created_at")
        gallery = LandingGalleryItem.objects.filter(is_active=True).order_by("sort_order", "created_at")
        ctx = {"request": request}
        return Response(
            {
                "active": True,
                "settings": LandingPageSettingsSerializer(settings_obj, context=ctx).data,
                "benefits": LandingBenefitSerializer(benefits, many=True).data,
                "gallery": LandingGalleryItemSerializer(gallery, many=True, context=ctx).data,
            }
        )


def _knowledge_audiences(user) -> list[str] | None:
    """None = see all (superuser)."""
    if getattr(user, "is_superuser", False):
        return None
    if getattr(user, "is_staff", False):
        names: list[str] = []
        profile = getattr(user, "staff_profile", None)
        if profile is not None:
            names = [str(n).lower() for n in profile.roles.values_list("name", flat=True)]
        if any("finance" in n for n in names):
            return ["all", "staff", "finance"]
        return ["all", "staff"]
    return ["all", "associate"]


class KnowledgeItemViewSet(viewsets.ModelViewSet):
    serializer_class = KnowledgeItemSerializer
    filterset_fields = ["audience", "media_type", "is_published"]
    search_fields = ["title", "body"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = KnowledgeItem.objects.all()
        user = self.request.user
        allowed = _knowledge_audiences(user)
        if not (user.is_staff or user.is_superuser):
            qs = qs.filter(is_published=True)
        if allowed is not None:
            qs = qs.filter(audience__in=allowed)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
