from rest_framework import serializers

from core.media_urls import absolute_media_url
from wallets.fund_packages import format_lakh, payment_method_label
from wallets.models import FundTransferRequest, LedgerEntry, Wallet
from wallets.visibility import visible_wallet_balance


class WalletSerializer(serializers.ModelSerializer):
    associate_id = serializers.CharField(source="associate.associate_id", read_only=True)
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = (
            "id",
            "associate_id",
            "wallet_type",
            "balance",
            "held_balance",
            "currency",
            "updated_at",
        )

    def get_balance(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and (user.is_staff or user.is_superuser):
            return str(obj.balance or 0)
        return str(visible_wallet_balance(obj))


class LedgerEntrySerializer(serializers.ModelSerializer):
    wallet_type = serializers.CharField(source="wallet.wallet_type", read_only=True)
    associate_id = serializers.CharField(source="wallet.associate.associate_id", read_only=True)

    class Meta:
        model = LedgerEntry
        fields = (
            "id",
            "associate_id",
            "wallet_type",
            "entry_type",
            "amount",
            "balance_after",
            "reference",
            "narration",
            "meta",
            "created_at",
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        is_staff = bool(user and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)))
        if not is_staff:
            meta = dict(data.get("meta") or {})
            for key in ("gross_amount", "admin_charge", "admin_charge_percent", "net_amount"):
                meta.pop(key, None)
            data["meta"] = meta
        return data


class FundTransferRequestSerializer(serializers.ModelSerializer):
    requester_associate_id = serializers.CharField(source="requester.associate_id", read_only=True)
    requester_name = serializers.SerializerMethodField()
    beneficiary_associate_id = serializers.CharField(
        source="beneficiary.associate_id", read_only=True
    )
    beneficiary_name = serializers.SerializerMethodField()
    amount_label = serializers.SerializerMethodField()
    payment_method_label = serializers.SerializerMethodField()
    reviewed_by_email = serializers.SerializerMethodField()
    proof_url = serializers.SerializerMethodField()

    class Meta:
        model = FundTransferRequest
        fields = (
            "id",
            "requester_associate_id",
            "requester_name",
            "beneficiary_associate_id",
            "beneficiary_name",
            "amount",
            "amount_label",
            "wallet_type",
            "payment_method",
            "payment_method_label",
            "utr",
            "proof_url",
            "note",
            "status",
            "rejection_reason",
            "reviewed_by_email",
            "reviewed_at",
            "created_at",
        )
        read_only_fields = fields

    def get_requester_name(self, obj):
        user = obj.requester.user
        return user.get_full_name() or user.username or obj.requester.associate_id

    def get_beneficiary_name(self, obj):
        user = obj.beneficiary.user
        return user.get_full_name() or user.username or obj.beneficiary.associate_id

    def get_amount_label(self, obj):
        return format_lakh(obj.amount)

    def get_payment_method_label(self, obj):
        return payment_method_label(obj.payment_method)

    def get_reviewed_by_email(self, obj):
        return getattr(obj.reviewed_by, "email", "") or ""

    def get_proof_url(self, obj):
        return absolute_media_url(
            obj.proof, self.context.get("request"), version=getattr(obj, "updated_at", None)
        )
