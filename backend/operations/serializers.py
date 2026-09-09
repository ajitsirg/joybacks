from decimal import Decimal

from rest_framework import serializers

from core.media_urls import absolute_media_url
from operations.models import DepositRequest, KYCSubmission, WithdrawalRequest
from wallets.models import Wallet


class KYCSerializer(serializers.ModelSerializer):
    associate_id = serializers.CharField(source="associate.associate_id", read_only=True)
    username = serializers.CharField(source="associate.user.username", read_only=True)
    associate_status = serializers.CharField(source="associate.status", read_only=True)
    associate_name = serializers.SerializerMethodField()
    kyc_verified = serializers.BooleanField(source="associate.kyc_verified", read_only=True)
    profile_photo_url = serializers.SerializerMethodField()
    aadhaar_document_url = serializers.SerializerMethodField()
    aadhaar_front_url = serializers.SerializerMethodField()
    aadhaar_back_url = serializers.SerializerMethodField()
    aadhaar_attached = serializers.SerializerMethodField()
    pan_document_url = serializers.SerializerMethodField()
    bank_document_url = serializers.SerializerMethodField()
    aadhaar_front = serializers.FileField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = KYCSubmission
        fields = (
            "id",
            "associate_id",
            "username",
            "associate_status",
            "associate_name",
            "kyc_verified",
            "full_name",
            "pan",
            "aadhaar",
            "bank_name",
            "account_number",
            "ifsc",
            "upi_id",
            "profile_photo",
            "aadhaar_document",
            "aadhaar_front",
            "aadhaar_back",
            "pan_document",
            "bank_document",
            "document_front",
            "document_back",
            "profile_photo_url",
            "aadhaar_document_url",
            "aadhaar_front_url",
            "aadhaar_back_url",
            "aadhaar_attached",
            "pan_document_url",
            "bank_document_url",
            "status",
            "rejection_reason",
            "created_at",
            "reviewed_at",
        )
        read_only_fields = ("status", "rejection_reason", "reviewed_at", "aadhaar_attached")
        extra_kwargs = {
            "profile_photo": {"write_only": True, "required": False},
            "aadhaar_document": {"write_only": True, "required": False},
            "aadhaar_back": {"write_only": True, "required": False},
            "pan_document": {"write_only": True, "required": False},
            "bank_document": {"write_only": True, "required": False},
            "document_front": {"write_only": True, "required": False},
            "document_back": {"write_only": True, "required": False},
        }

    def _abs(self, f, obj):
        return absolute_media_url(f, self.context.get("request"), version=getattr(obj, "updated_at", None))

    def get_associate_name(self, obj):
        user = getattr(obj.associate, "user", None)
        if not user:
            return obj.full_name or ""
        name = (user.get_full_name() or "").strip()
        return name or obj.full_name or user.username

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

    def validate_pan(self, value):
        return (value or "").strip().upper()

    def validate_ifsc(self, value):
        return (value or "").strip().upper()

    def validate_aadhaar(self, value):
        digits = "".join(ch for ch in str(value or "") if ch.isdigit())
        return digits or str(value or "").strip()

    def create(self, validated_data):
        front = validated_data.pop("aadhaar_front", None)
        if front and not validated_data.get("aadhaar_document"):
            validated_data["aadhaar_document"] = front
        return super().create(validated_data)

    def update(self, instance, validated_data):
        front = validated_data.pop("aadhaar_front", None)
        if front:
            validated_data["aadhaar_document"] = front
        return super().update(instance, validated_data)


class DepositSerializer(serializers.ModelSerializer):
    associate_id = serializers.CharField(source="associate.associate_id", read_only=True)
    username = serializers.CharField(source="associate.user.username", read_only=True)

    class Meta:
        model = DepositRequest
        fields = (
            "id",
            "associate_id",
            "username",
            "amount",
            "wallet_type",
            "transaction_id",
            "status",
            "rejection_reason",
            "created_at",
            "applied_at",
            "reviewed_at",
        )
        read_only_fields = (
            "status",
            "rejection_reason",
            "applied_at",
            "reviewed_at",
            "associate_id",
            "username",
        )

    def validate_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Amount must be positive.")
        return value

    def validate_wallet_type(self, value):
        if value not in {Wallet.WalletType.MAIN, Wallet.WalletType.PERSONAL}:
            raise serializers.ValidationError("Deposits are allowed only to main or personal wallets.")
        return value

    def validate_transaction_id(self, value):
        reference = " ".join((value or "").strip().split())
        if not reference:
            raise serializers.ValidationError("Payment reference is required.")
        existing = DepositRequest.objects.filter(transaction_id__iexact=reference)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError("This payment reference has already been submitted.")
        return reference


class WithdrawalSerializer(serializers.ModelSerializer):
    associate_id = serializers.CharField(source="associate.associate_id", read_only=True)
    username = serializers.CharField(source="associate.user.username", read_only=True)

    class Meta:
        model = WithdrawalRequest
        fields = (
            "id",
            "associate_id",
            "username",
            "amount",
            "charge_amount",
            "net_amount",
            "bank_detail",
            "status",
            "requires_maker_checker",
            "verified_by",
            "verified_at",
            "rejection_reason",
            "created_at",
            "transferred_at",
            "reviewed_at",
        )
        read_only_fields = (
            "charge_amount",
            "net_amount",
            "status",
            "requires_maker_checker",
            "verified_by",
            "verified_at",
            "rejection_reason",
            "transferred_at",
            "reviewed_at",
        )

    def validate_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Amount must be positive.")
        return value

    def validate_bank_detail(self, value):
        value = " ".join((value or "").strip().split())
        if not value:
            raise serializers.ValidationError("Bank details are required.")
        return value


class ReviewActionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")
