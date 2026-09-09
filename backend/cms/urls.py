from django.urls import include, path
from rest_framework.routers import DefaultRouter

from cms.views import HelpTicketViewSet, KnowledgeItemViewSet, LandingPageView, NewsViewSet, QRWalletViewSet

router = DefaultRouter()
router.register("news", NewsViewSet)
router.register("help", HelpTicketViewSet)
router.register("qr-wallets", QRWalletViewSet)
router.register("knowledge", KnowledgeItemViewSet, basename="knowledge")

urlpatterns = [
    path("landing/", LandingPageView.as_view(), name="cms-landing"),
    path("", include(router.urls)),
]
