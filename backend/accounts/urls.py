from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.views import (
    ForgotPasswordView,
    ImpersonateView,
    LoginView,
    MeView,
    OTPLoginView,
    PermissionListView,
    RefreshView,
    RequestOTPLoginView,
    ResetPasswordView,
    RoleViewSet,
    StaffViewSet,
)

router = DefaultRouter()
router.register("roles", RoleViewSet, basename="roles")
router.register("staff", StaffViewSet, basename="staff")

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("impersonate/", ImpersonateView.as_view(), name="impersonate"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("otp/request/", RequestOTPLoginView.as_view(), name="otp-request"),
    path("otp/login/", OTPLoginView.as_view(), name="otp-login"),
    path("permissions/", PermissionListView.as_view(), name="permissions"),
    path("", include(router.urls)),
]
