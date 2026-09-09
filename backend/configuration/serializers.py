from decimal import Decimal

from rest_framework import serializers

from configuration.models import (
    ActivationRule,
    CompanySettings,
    GenealogySettings,
    LevelIncomePlan,
    LevelIncomeSlab,
    PerformanceIncomePlan,
    PerformanceIncomeSlab,
    ROIPlan,
    RewardMaster,
    WithdrawalSettings,
)


class CompanySettingsSerializer(serializers.ModelSerializer):
    reward_poster_image_url = serializers.SerializerMethodField()

    class Meta:
        model = CompanySettings
        fields = [f.name for f in CompanySettings._meta.fields] + ["reward_poster_image_url"]

    def get_reward_poster_image_url(self, obj: CompanySettings) -> str | None:
        if not obj.reward_poster_image:
            return None
        request = self.context.get("request")
        url = obj.reward_poster_image.url
        if request:
            return request.build_absolute_uri(url)
        return url


class GenealogySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenealogySettings
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["effective_max_legs"] = instance.effective_max_legs()
        return data


class WithdrawalSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalSettings
        fields = "__all__"


class ActivationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivationRule
        fields = "__all__"


class LevelIncomeSlabSerializer(serializers.ModelSerializer):
    class Meta:
        model = LevelIncomeSlab
        fields = ("id", "level", "percent", "title", "is_active")

    def validate_percent(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Percentage cannot be negative.")
        return value

    def validate_level(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("Level must be at least 1.")
        return value


class LevelIncomePlanSerializer(serializers.ModelSerializer):
    slabs = LevelIncomeSlabSerializer(many=True, read_only=True)
    poster_image_url = serializers.SerializerMethodField()
    total_percent = serializers.SerializerMethodField()

    class Meta:
        model = LevelIncomePlan
        fields = (
            "id",
            "name",
            "code",
            "max_levels",
            "is_active",
            "description",
            "tagline",
            "poster_image",
            "poster_image_url",
            "total_percent",
            "slabs",
        )

    def get_poster_image_url(self, obj: LevelIncomePlan) -> str | None:
        if not obj.poster_image:
            return None
        request = self.context.get("request")
        url = obj.poster_image.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_total_percent(self, obj: LevelIncomePlan) -> str:
        total = sum(
            (s.percent for s in obj.slabs.all() if s.is_active),
            start=Decimal("0"),
        )
        return str(total)


class PerformanceIncomeSlabSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceIncomeSlab
        fields = ("id", "level", "percent", "required_directs", "min_business", "is_active")

    def validate_percent(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Percentage cannot be negative.")
        return value

    def validate_required_directs(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Required directs cannot be negative.")
        return value

    def validate_level(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("Level must be at least 1.")
        return value


class PerformanceIncomePlanSerializer(serializers.ModelSerializer):
    slabs = PerformanceIncomeSlabSerializer(many=True, read_only=True)
    poster_image_url = serializers.SerializerMethodField()
    total_percent = serializers.SerializerMethodField()

    class Meta:
        model = PerformanceIncomePlan
        fields = (
            "id",
            "name",
            "code",
            "max_levels",
            "is_active",
            "poster_image",
            "poster_image_url",
            "total_percent",
            "slabs",
        )

    def get_poster_image_url(self, obj: PerformanceIncomePlan) -> str | None:
        if not obj.poster_image:
            return None
        request = self.context.get("request")
        url = obj.poster_image.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_total_percent(self, obj: PerformanceIncomePlan) -> str:
        total = sum(
            (s.percent for s in obj.slabs.all() if s.is_active),
            start=Decimal("0"),
        )
        return str(total)


class ROIPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = ROIPlan
        fields = "__all__"


class RewardMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardMaster
        fields = "__all__"
