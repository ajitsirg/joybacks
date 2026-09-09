from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from accounts.models import Permission, Role, StaffProfile
from accounts.services import RBACService
from core.validators import validate_email_address

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    """Associate: username (JOY…) + password. Staff: email + password."""

    email = serializers.EmailField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    mobile = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    remember_me = serializers.BooleanField(default=False)

    def validate_email(self, value: str) -> str:
        if not (value or "").strip():
            return ""
        try:
            return validate_email_address(value, required=True)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0] if exc.messages else str(exc)) from exc

    def validate(self, attrs):
        if not attrs.get("username") and not attrs.get("email"):
            raise serializers.ValidationError("Provide username (JOY…) or staff email.")
        return attrs


class UserSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    associate = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "phone",
            "user_type",
            "is_staff",
            "is_superuser",
            "last_login",
            "last_login_ip",
            "permissions",
            "roles",
            "associate",
        )
        read_only_fields = ("last_login", "last_login_ip")

    def get_permissions(self, obj):
        return RBACService.user_permissions(obj)

    def get_roles(self, obj):
        if hasattr(obj, "staff_profile"):
            return list(obj.staff_profile.roles.values_list("name", flat=True))
        return []

    def get_associate(self, obj):
        from core.media_urls import absolute_media_url

        assoc = getattr(obj, "associate", None)
        if not assoc:
            return None
        waiting = ""
        if assoc.status == "pending":
            waiting = "Wait for your admin approval"
        elif assoc.status == "rejected":
            waiting = assoc.rejection_reason or "Your join request was rejected by your lead"
        elif assoc.status == "inactive":
            waiting = "Invest at least ₹2,20,000 to become Active"
        kyc = assoc.kyc_submissions.order_by("-created_at").first()
        photo_url = None
        if kyc and kyc.profile_photo:
            photo_url = absolute_media_url(
                kyc.profile_photo,
                self.context.get("request"),
                version=getattr(kyc, "updated_at", None),
            )
        return {
            "associate_id": assoc.associate_id,
            "username": assoc.associate_id,
            "mobile": assoc.mobile,
            "referral_code": assoc.referral_code,
            "card_tier": assoc.card_tier,
            "flag_color": assoc.flag_color,
            "join_amount": str(assoc.join_amount),
            "personal_business": str(assoc.personal_business),
            "total_business": str(assoc.total_business),
            "earning_level": int(assoc.earning_level or 0),
            "earning_level_name": assoc.earning_level_name or "",
            "reward_level": int(assoc.earning_level or 0),
            "reward_level_name": assoc.earning_level_name or "",
            "performance_level": int(assoc.performance_level or 0),
            "performance_level_name": assoc.performance_level_name or "",
            "lead_reference": assoc.lead_reference,
            "status": assoc.status,
            "kyc_verified": assoc.kyc_verified,
            "can_view_admin_history": bool(assoc.can_view_admin_history),
            "can_view_reward_achievers": bool(assoc.can_view_reward_achievers),
            "can_fund_transfer": bool(assoc.can_fund_transfer),
            "rejection_reason": assoc.rejection_reason,
            "waiting_message": waiting,
            "profile_photo_url": photo_url,
        }


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()
    remember_me = serializers.BooleanField(required=False)


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ("id", "code", "name", "module", "description")


class RoleSerializer(serializers.ModelSerializer):
    permission_ids = serializers.PrimaryKeyRelatedField(
        source="permissions",
        many=True,
        queryset=Permission.objects.all(),
        required=False,
    )
    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Role
        fields = (
            "id",
            "name",
            "description",
            "is_system",
            "permissions",
            "permission_ids",
            "created_at",
            "updated_at",
        )


class StaffSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", required=False)
    first_name = serializers.CharField(source="user.first_name", required=False, allow_blank=True)
    last_name = serializers.CharField(source="user.last_name", required=False, allow_blank=True)
    name = serializers.SerializerMethodField()
    roles = RoleSerializer(many=True, read_only=True)
    role_ids = serializers.PrimaryKeyRelatedField(
        source="roles",
        many=True,
        queryset=Role.objects.all(),
        required=False,
    )
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=6)
    last_login_at = serializers.DateTimeField(source="user.last_login", read_only=True)
    last_login_ip = serializers.IPAddressField(source="user.last_login_ip", read_only=True, allow_null=True)
    is_active = serializers.BooleanField(source="user.is_active", required=False)

    class Meta:
        model = StaffProfile
        fields = (
            "id",
            "employee_code",
            "email",
            "first_name",
            "last_name",
            "name",
            "department",
            "is_suspended",
            "is_active",
            "roles",
            "role_ids",
            "password",
            "last_login_at",
            "last_login_ip",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def create(self, validated_data):
        from django.db import transaction

        user_data = validated_data.pop("user", {})
        roles = validated_data.pop("roles", [])
        password = validated_data.pop("password", None) or "ChangeMe@123"
        email = (user_data.get("email") or "").strip().lower()
        if not email:
            raise serializers.ValidationError({"email": "Email is required"})
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({"email": "Email already in use"})

        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                password=password,
                username=email,
                first_name=str(user_data.get("first_name") or "").strip(),
                last_name=str(user_data.get("last_name") or "").strip(),
                user_type=User.UserType.STAFF,
                is_staff=True,
                is_active=True,
            )
            code = str(validated_data.get("employee_code") or "").strip()
            if not code:
                code = f"JC-STAFF-{user.id:04d}"
                validated_data["employee_code"] = code
            profile = StaffProfile.objects.create(user=user, **validated_data)
            if roles:
                profile.roles.set(roles)
            from accounts.rbac_seed import sync_staff_django_groups

            sync_staff_django_groups(user)
        return profile

    def update(self, instance, validated_data):
        from django.db import transaction

        user_data = validated_data.pop("user", {})
        roles = validated_data.pop("roles", None)
        password = validated_data.pop("password", None)

        with transaction.atomic():
            user = instance.user
            if "email" in user_data and user_data["email"]:
                email = str(user_data["email"]).strip().lower()
                if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
                    raise serializers.ValidationError({"email": "Email already in use"})
                user.email = email
                if user.username == user.email or "@" in (user.username or ""):
                    user.username = email
            if "first_name" in user_data:
                user.first_name = str(user_data.get("first_name") or "").strip()
            if "last_name" in user_data:
                user.last_name = str(user_data.get("last_name") or "").strip()
            if "is_active" in user_data:
                user.is_active = bool(user_data["is_active"])
            if password:
                user.set_password(password)
            user.is_staff = True
            user.user_type = User.UserType.STAFF
            user.save()

            for key, val in validated_data.items():
                setattr(instance, key, val)
            # Keep suspension in sync with active flag when toggled via is_suspended
            if "is_suspended" in validated_data:
                if validated_data["is_suspended"]:
                    user.is_active = False
                    user.save(update_fields=["is_active"])
                elif "is_active" not in user_data:
                    user.is_active = True
                    user.save(update_fields=["is_active"])
            instance.save()
            if roles is not None:
                instance.roles.set(roles)
            from accounts.rbac_seed import sync_staff_django_groups

            sync_staff_django_groups(user)
        return instance


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        try:
            return validate_email_address(value, required=True)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0] if exc.messages else str(exc)) from exc


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8)

    def validate_email(self, value: str) -> str:
        try:
            return validate_email_address(value, required=True)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0] if exc.messages else str(exc)) from exc


class OTPLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate_email(self, value: str) -> str:
        try:
            return validate_email_address(value, required=True)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0] if exc.messages else str(exc)) from exc
