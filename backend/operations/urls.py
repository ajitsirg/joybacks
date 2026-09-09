from django.urls import include, path
from rest_framework.routers import DefaultRouter

from operations.views import DepositViewSet, KYCViewSet, WithdrawalViewSet

router = DefaultRouter()
router.register("kyc", KYCViewSet, basename="kyc")
router.register("deposits", DepositViewSet, basename="deposits")
router.register("withdrawals", WithdrawalViewSet, basename="withdrawals")

urlpatterns = [path("", include(router.urls))]
