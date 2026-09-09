from django.urls import include, path
from rest_framework.routers import DefaultRouter

from configuration.views import (
    ActivationRuleViewSet,
    CompanySettingsViewSet,
    GenealogySettingsViewSet,
    LevelIncomePlanViewSet,
    PerformanceIncomePlanViewSet,
    ROIPlanViewSet,
    RewardMasterViewSet,
    RuntimeConfigView,
    WithdrawalSettingsViewSet,
)

router = DefaultRouter()
router.register("company", CompanySettingsViewSet)
router.register("genealogy", GenealogySettingsViewSet)
router.register("withdrawal", WithdrawalSettingsViewSet)
router.register("activation", ActivationRuleViewSet)
router.register("level-income", LevelIncomePlanViewSet)
router.register("performance-income", PerformanceIncomePlanViewSet)
router.register("roi", ROIPlanViewSet)
router.register("rewards", RewardMasterViewSet)

urlpatterns = [
    path("runtime/", RuntimeConfigView.as_view(), name="runtime-config"),
    path("", include(router.urls)),
]
