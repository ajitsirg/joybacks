from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.models import Permission, Role, StaffProfile
from accounts.serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    OTPLoginSerializer,
    PermissionSerializer,
    ResetPasswordSerializer,
    RoleSerializer,
    StaffSerializer,
    TokenResponseSerializer,
    UserSerializer,
)
from accounts.services import AuthService
from audit.middleware import get_request_ip, get_user_agent

User = get_user_model()


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=LoginSerializer, responses=TokenResponseSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = AuthService.login(
                email=serializer.validated_data.get("email", ""),
                username=serializer.validated_data.get("username", ""),
                mobile=serializer.validated_data.get("mobile", ""),
                password=serializer.validated_data["password"],
                remember_me=serializer.validated_data.get("remember_me", False),
                ip=get_request_ip(),
                user_agent=get_user_agent(),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(
            {
                "access": result["access"],
                "refresh": result["refresh"],
                "remember_me": result.get("remember_me", False),
                "user": UserSerializer(result["user"], context={"request": request}).data,
            }
        )


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user, context={"request": request}).data)


class ImpersonateView(APIView):
    """Staff/superadmin: issue tokens as an associate (Login-as)."""

    def post(self, request):
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({"detail": "Staff only"}, status=status.HTTP_403_FORBIDDEN)
        associate_id = str(request.data.get("associate_id") or "").strip().upper()
        if not associate_id:
            return Response({"detail": "associate_id required"}, status=status.HTTP_400_BAD_REQUEST)
        from associates.models import Associate
        from audit.services import write_audit

        assoc = (
            Associate.objects.select_related("user")
            .filter(associate_id__iexact=associate_id, is_deleted=False)
            .first()
        )
        if not assoc or not assoc.user_id:
            return Response({"detail": "Associate not found"}, status=status.HTTP_404_NOT_FOUND)
        if not assoc.user.is_active:
            return Response({"detail": "User account is inactive"}, status=status.HTTP_400_BAD_REQUEST)
        result = AuthService.issue_tokens(assoc.user)
        write_audit(
            actor=request.user,
            action="auth.impersonate",
            module="accounts",
            object_type="Associate",
            object_id=str(assoc.id),
            ip_address=get_request_ip(),
            metadata={"associate_id": assoc.associate_id, "target_user_id": assoc.user_id},
        )
        return Response(
            {
                "access": result["access"],
                "refresh": result["refresh"],
                "user": UserSerializer(result["user"], context={"request": request}).data,
            }
        )


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=ForgotPasswordSerializer)
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        code = AuthService.create_otp(phone_or_email=email, purpose="reset")
        # Dev convenience: return OTP when DEBUG — remove in production gateway wiring
        payload = {"detail": "OTP sent if account exists."}
        from django.conf import settings

        if settings.DEBUG and User.objects.filter(email__iexact=email).exists():
            payload["debug_otp"] = code
        return Response(payload)


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=ResetPasswordSerializer)
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        ok = AuthService.verify_otp(
            phone_or_email=data["email"],
            purpose="reset",
            code=data["otp"],
        )
        if not ok:
            return Response({"detail": "Invalid or expired OTP"}, status=400)
        try:
            user = User.objects.get(email__iexact=data["email"])
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=404)
        new_password = data["new_password"]
        user.set_password(new_password)
        user.save(update_fields=["password"])
        # Keep staff-visible plaintext in sync for associates
        from associates.models import Associate

        assoc = Associate.objects.filter(user=user, is_deleted=False).first()
        if assoc:
            assoc.login_password = new_password
            assoc.save(update_fields=["login_password", "updated_at"])
        return Response({"detail": "Password updated"})


class RequestOTPLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        if not email:
            return Response({"detail": "Email required"}, status=400)
        code = AuthService.create_otp(phone_or_email=email, purpose="login")
        payload = {"detail": "OTP sent if account exists."}
        from django.conf import settings

        if settings.DEBUG and User.objects.filter(email__iexact=email).exists():
            payload["debug_otp"] = code
        return Response(payload)


class OTPLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=OTPLoginSerializer, responses=TokenResponseSerializer)
    def post(self, request):
        serializer = OTPLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        ok = AuthService.verify_otp(
            phone_or_email=email,
            purpose="login",
            code=serializer.validated_data["otp"],
        )
        if not ok:
            return Response({"detail": "Invalid or expired OTP"}, status=401)
        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=404)
        result = AuthService.issue_tokens(user)
        return Response(
            {
                "access": result["access"],
                "refresh": result["refresh"],
                "user": UserSerializer(user, context={"request": request}).data,
            }
        )


class PermissionListView(generics.ListAPIView):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ["module"]
    search_fields = ["code", "name"]


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.prefetch_related("permissions").all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAdminUser]
    search_fields = ["name"]


class StaffViewSet(viewsets.ModelViewSet):
    """List / create / update staff profiles (edit details + allot roles). Soft-suspend instead of delete."""

    queryset = StaffProfile.objects.select_related("user").prefetch_related("roles", "roles__permissions").filter(
        is_deleted=False
    )
    serializer_class = StaffSerializer
    permission_classes = [permissions.IsAdminUser]
    http_method_names = ["get", "post", "patch", "put", "head", "options"]
    search_fields = ["employee_code", "user__email", "user__first_name", "user__last_name"]

    def perform_destroy(self, instance):
        # Never hard-delete staff — hide/deactivate only
        instance.is_suspended = True
        instance.is_deleted = False
        instance.save(update_fields=["is_suspended", "updated_at"])
        user = instance.user
        user.is_active = False
        user.save(update_fields=["is_active"])


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]
