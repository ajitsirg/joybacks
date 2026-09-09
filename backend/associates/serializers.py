from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from associates.models import PLATINUM_JOIN_AMOUNT, Associate, tier_from_amount
from core.validators import validate_email_address, validate_mobile
from operations.models import KYCSubmission


class AssociateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    username = serializers.CharField(source="associate_id", read_only=True)
    name = serializers.SerializerMethodField()
    sponsor_id = serializers.CharField(source="sponsor_associate_id", read_only=True)
    waiting_message = serializers.SerializerMethodField()
    kyc = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    wallet_balance = serializers.SerializerMethodField()
    fund_wallet = serializers.SerializerMethodField()
    last_login_at = serializers.DateTimeField(source="user.last_login", read_only=True, allow_null=True)
    last_login_ip = serializers.IPAddressField(source="user.last_login_ip", read_only=True, allow_null=True)
    # Alias: Reward Achievement ladder == earning_level
    reward_level = serializers.IntegerField(source="earning_level", read_only=True)
    reward_level_name = serializers.CharField(source="earning_level_name", read_only=True)
    # Tree depth from company root; leg depth from viewer (when available)
    tree_level = serializers.SerializerMethodField()
    leg_level = serializers.SerializerMethodField()

    class Meta:
        model = Associate
        fields = (
            "id",
            "associate_id",
            "username",
            "referral_code",
            "email",
            "first_name",
            "last_name",
            "name",
            "mobile",
            "status",
            "sponsor_id",
            "lead_reference",
            "join_amount",
            "card_tier",
            "flag_color",
            "kyc_verified",
            "can_view_admin_history",
            "can_view_reward_achievers",
            "can_fund_transfer",
            "login_password",
            "rejection_reason",
            "waiting_message",
            "total_business",
            "personal_business",
            "earning_level",
            "earning_level_name",
            "reward_level",
            "reward_level_name",
            "performance_level",
            "performance_level_name",
            "tree_level",
            "leg_level",
            "direct_count",
            "direct_active_count",
            "wallet_balance",
            "fund_wallet",
            "city",
            "state",
            "country",
            "activated_at",
            "created_at",
            "last_login_at",
            "last_login_ip",
            "kyc",
            "can_edit",
        )

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_waiting_message(self, obj):
        if obj.status == Associate.Status.PENDING:
            return "Wait for your admin approval"
        if obj.status == Associate.Status.REJECTED:
            return obj.rejection_reason or "Your join request was rejected by your lead"
        if obj.status == Associate.Status.INACTIVE:
            return "Invest at least ₹2,20,000 to become Active"
        return ""

    def get_kyc(self, obj):
        kyc = obj.kyc_submissions.order_by("-created_at").first()
        if not kyc:
            return None
        return JoinKycDetailSerializer(kyc, context=self.context).data

    def get_can_edit(self, obj):
        request = self.context.get("request")
        if not request or not getattr(request, "user", None):
            return False
        from associates.services import can_edit_associate

        return can_edit_associate(request.user, obj)

    def _wallet_balance(self, obj, wallet_type: str) -> str:
        wallets = getattr(obj, "_prefetched_objects_cache", {}).get("wallets")
        if wallets is not None:
            for w in wallets:
                if w.wallet_type == wallet_type and not getattr(w, "is_deleted", False):
                    return str(w.balance)
            return "0.00"
        w = obj.wallets.filter(wallet_type=wallet_type, is_deleted=False).first()
        return str(w.balance) if w else "0.00"

    def get_wallet_balance(self, obj):
        return self._wallet_balance(obj, "main")

    def get_fund_wallet(self, obj):
        return self._wallet_balance(obj, "income")

    def get_tree_level(self, obj):
        val = getattr(obj, "tree_level", None)
        if val is not None:
            return int(val)
        node = getattr(obj, "genealogy_node", None)
        if node is not None:
            return int(node.depth or 0)
        return 0

    def get_leg_level(self, obj):
        val = getattr(obj, "leg_level", None)
        if val is not None:
            return int(val)
        return 0

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        # Only staff may see the admin-visible password copy
        if not user or not (user.is_staff or user.is_superuser):
            data.pop("login_password", None)
        # Full KYC / contact details only for self or staff — list stays summary for under-leg
        from associates.services import can_view_associate_details

        if not can_view_associate_details(user, instance):
            data.pop("kyc", None)
            data.pop("email", None)
            data.pop("last_login_at", None)
            data.pop("last_login_ip", None)
            data.pop("rejection_reason", None)
            # Keep mobile/name/id for team list & fund transfer; hide bank-adjacent city detail optional
        return data


class AssociateUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=80, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=80, required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    mobile = serializers.CharField(max_length=20, required=False)
    city = serializers.CharField(max_length=80, required=False, allow_blank=True)
    state = serializers.CharField(max_length=80, required=False, allow_blank=True)
    country = serializers.CharField(max_length=80, required=False, allow_blank=True)
    full_name = serializers.CharField(max_length=160, required=False, allow_blank=True)
    pan = serializers.CharField(max_length=20, required=False, allow_blank=True)
    aadhaar = serializers.CharField(max_length=20, required=False, allow_blank=True)
    bank_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    account_number = serializers.CharField(max_length=40, required=False, allow_blank=True)
    ifsc = serializers.CharField(max_length=20, required=False, allow_blank=True)
    upi_id = serializers.CharField(max_length=120, required=False, allow_blank=True)
    profile_photo = serializers.ImageField(required=False, allow_null=True)
    aadhaar_document = serializers.FileField(required=False, allow_null=True)
    aadhaar_front = serializers.FileField(required=False, allow_null=True)
    aadhaar_back = serializers.FileField(required=False, allow_null=True)
    pan_document = serializers.FileField(required=False, allow_null=True)
    bank_document = serializers.FileField(required=False, allow_null=True)
    password = serializers.CharField(min_length=6, required=False, allow_blank=True, write_only=True)
    confirm_password = serializers.CharField(
        min_length=6, required=False, allow_blank=True, write_only=True
    )
    # Staff / superadmin only (enforced in service)
    status = serializers.CharField(max_length=20, required=False)
    can_view_admin_history = serializers.BooleanField(required=False)
    can_view_reward_achievers = serializers.BooleanField(required=False)
    can_fund_transfer = serializers.BooleanField(required=False)


class AssociateRegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=80)
    last_name = serializers.CharField(max_length=80, allow_blank=True, required=False, default="")
    mobile = serializers.CharField(max_length=20)
    password = serializers.CharField(min_length=6, write_only=True)
    lead_reference = serializers.CharField(max_length=40, help_text="Mandatory lead / J-username of sponsor")
    join_amount = serializers.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(max_length=6, required=False, allow_blank=True, default="")
    pan = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    aadhaar = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    bank_name = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    account_number = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")
    ifsc = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    upi_id = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    profile_photo = serializers.ImageField(required=False, allow_null=True, default=None)
    aadhaar_document = serializers.FileField(required=False, allow_null=True, default=None)
    aadhaar_front = serializers.FileField(required=False, allow_null=True, default=None)
    aadhaar_back = serializers.FileField(required=False, allow_null=True, default=None)
    pan_document = serializers.FileField(required=False, allow_null=True, default=None)
    bank_document = serializers.FileField(required=False, allow_null=True, default=None)

    def validate_mobile(self, value: str) -> str:
        try:
            return validate_mobile(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0] if exc.messages else str(exc)) from exc

    def validate_email(self, value: str) -> str:
        try:
            return validate_email_address(value, required=True)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0] if exc.messages else str(exc)) from exc

    def validate_join_amount(self, value: Decimal) -> Decimal:
        value = Decimal(value or 0)
        if value < 0:
            raise serializers.ValidationError("Join amount cannot be negative")
        return value

    def validate(self, attrs):
        amount = Decimal(attrs.get("join_amount") or 0)
        tier, flag = tier_from_amount(amount)
        attrs["card_tier"] = tier
        attrs["flag_color"] = flag
        attrs["platinum_amount"] = str(PLATINUM_JOIN_AMOUNT)
        return attrs


class JoinPreviewSerializer(serializers.Serializer):
    join_amount = serializers.DecimalField(max_digits=16, decimal_places=2)

    def to_representation(self, instance):
        amount = Decimal(instance.get("join_amount") or 0)
        tier, flag = tier_from_amount(amount)
        silver_min = (PLATINUM_JOIN_AMOUNT * Decimal("10") / Decimal("100")).quantize(Decimal("0.01"))
        return {
            "join_amount": str(amount),
            "card_tier": tier,
            "flag_color": flag,
            "labels": {
                "platinum": {"amount": str(PLATINUM_JOIN_AMOUNT), "flag": "green", "card": "Platinum"},
                "silver": {"amount_min": str(silver_min), "flag": "green", "card": "Silver"},
                "gray": {"amount": "0", "flag": "gray", "card": "Gray"},
                "flags": {
                    "gray": "Joined — no investment yet",
                    "green": "Has investment",
                },
            },
        }


class JoinKycDetailSerializer(serializers.ModelSerializer):
    profile_photo_url = serializers.SerializerMethodField()
    aadhaar_document_url = serializers.SerializerMethodField()
    aadhaar_front_url = serializers.SerializerMethodField()
    aadhaar_back_url = serializers.SerializerMethodField()
    aadhaar_attached = serializers.SerializerMethodField()
    pan_document_url = serializers.SerializerMethodField()
    bank_document_url = serializers.SerializerMethodField()

    class Meta:
        model = KYCSubmission
        fields = (
            "id",
            "full_name",
            "pan",
            "aadhaar",
            "bank_name",
            "account_number",
            "ifsc",
            "upi_id",
            "status",
            "rejection_reason",
            "profile_photo_url",
            "aadhaar_document_url",
            "aadhaar_front_url",
            "aadhaar_back_url",
            "aadhaar_attached",
            "pan_document_url",
            "bank_document_url",
            "created_at",
            "reviewed_at",
        )

    def _abs(self, f, obj):
        from core.media_urls import absolute_media_url

        return absolute_media_url(f, self.context.get("request"), version=getattr(obj, "updated_at", None))

    def get_profile_photo_url(self, obj):
        return self._abs(obj.profile_photo, obj)

    def get_aadhaar_document_url(self, obj):
        return self._abs(obj.aadhaar_document, obj)

    def get_aadhaar_front_url(self, obj):
        return self._abs(obj.aadhaar_document, obj)

    def get_aadhaar_back_url(self, obj):
        return self._abs(obj.aadhaar_back, obj)

    def get_aadhaar_attached(self, obj):
        return bool(obj.aadhaar_attached)

    def get_pan_document_url(self, obj):
        return self._abs(obj.pan_document, obj)

    def get_bank_document_url(self, obj):
        return self._abs(obj.bank_document, obj)


class PendingJoinSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    username = serializers.CharField(source="associate_id", read_only=True)
    name = serializers.SerializerMethodField()
    kyc = serializers.SerializerMethodField()

    class Meta:
        model = Associate
        fields = (
            "id",
            "associate_id",
            "username",
            "name",
            "email",
            "mobile",
            "status",
            "join_amount",
            "card_tier",
            "flag_color",
            "lead_reference",
            "created_at",
            "kyc",
        )

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_kyc(self, obj):
        kyc = obj.kyc_submissions.order_by("-created_at").first()
        if not kyc:
            return None
        return JoinKycDetailSerializer(kyc, context=self.context).data


class LeaderReviewSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")
