from rest_framework import serializers

from commissions.models import AdminCharge, CommissionEntry, CommissionRun


class CommissionEntrySerializer(serializers.ModelSerializer):
    beneficiary_id = serializers.CharField(source="beneficiary.associate_id", read_only=True)
    source_id = serializers.CharField(source="source_associate.associate_id", read_only=True, default=None)
    buyer_id = serializers.CharField(source="source_associate.associate_id", read_only=True, default=None)
    run_type = serializers.CharField(source="run.run_type", read_only=True)
    commission_date = serializers.DateTimeField(source="created_at", read_only=True)
    investment_id = serializers.SerializerMethodField()

    class Meta:
        model = CommissionEntry
        fields = (
            "id",
            "run",
            "run_type",
            "beneficiary_id",
            "source_id",
            "buyer_id",
            "level",
            "growth_level",
            "percent",
            "sale_amount",
            "monthly_return_amount",
            "commission_month",
            "month_index",
            "investment_id",
            "amount",
            "admin_charge_amount",
            "net_amount",
            "wallet_type",
            "reference",
            "status",
            "narration",
            "commission_date",
            "created_at",
        )

    def get_investment_id(self, obj):
        return str(obj.investment_id) if obj.investment_id else None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        is_staff = bool(user and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)))
        if not is_staff:
            net = instance.net_amount if instance.net_amount else instance.amount
            data["amount"] = str(net)
            data.pop("admin_charge_amount", None)
            data.pop("net_amount", None)
        return data


class CommissionRunSerializer(serializers.ModelSerializer):
    entries = CommissionEntrySerializer(many=True, read_only=True)
    summary = serializers.SerializerMethodField()

    class Meta:
        model = CommissionRun
        fields = (
            "id",
            "run_type",
            "status",
            "source_reference",
            "source_amount",
            "notes",
            "summary",
            "entries",
            "created_at",
        )

    def get_summary(self, obj: CommissionRun) -> dict:
        return obj.payout_summary()


class AdminChargeSerializer(serializers.ModelSerializer):
    associate_id = serializers.CharField(source="associate.associate_id", read_only=True)
    associate_name = serializers.SerializerMethodField()
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = AdminCharge
        fields = (
            "id",
            "associate_id",
            "associate_name",
            "kind",
            "kind_label",
            "wallet_type",
            "gross_amount",
            "charge_percent",
            "charge_amount",
            "net_amount",
            "reference",
            "narration",
            "created_at",
        )

    def get_associate_name(self, obj):
        user = obj.associate.user
        return user.get_full_name() or user.username or obj.associate.associate_id
