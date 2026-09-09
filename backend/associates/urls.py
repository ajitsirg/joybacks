from django.urls import include, path
from rest_framework.routers import DefaultRouter

from associates.views import (
    ActivateAssociateView,
    AssociateViewSet,
    JoinPreviewView,
    LeaderApproveView,
    LeaderRejectView,
    PendingJoinsView,
    RegisterAssociateView,
    RequestRegisterOTPView,
    RewardLegsAssignView,
    RewardProgressView,
)

router = DefaultRouter()
router.register("", AssociateViewSet, basename="associates")

urlpatterns = [
    path("register/", RegisterAssociateView.as_view(), name="associate-register"),
    path("register/otp/", RequestRegisterOTPView.as_view(), name="associate-register-otp"),
    path("join-preview/", JoinPreviewView.as_view(), name="join-preview"),
    path("pending-joins/", PendingJoinsView.as_view(), name="pending-joins"),
    path("reward-progress/", RewardProgressView.as_view(), name="reward-progress"),
    path("reward-legs/", RewardLegsAssignView.as_view(), name="reward-legs"),
    path("<str:associate_id>/activate/", ActivateAssociateView.as_view(), name="associate-activate"),
    path("<str:associate_id>/leader-approve/", LeaderApproveView.as_view(), name="leader-approve"),
    path("<str:associate_id>/leader-reject/", LeaderRejectView.as_view(), name="leader-reject"),
    path("", include(router.urls)),
]
