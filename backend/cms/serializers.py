from rest_framework import serializers

from core.media_urls import absolute_media_url
from cms.models import (
    HelpTicket,
    KnowledgeItem,
    LandingBenefit,
    LandingGalleryItem,
    LandingPageSettings,
    NewsItem,
    QRWalletSetting,
)


class NewsItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsItem
        fields = "__all__"


class HelpTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpTicket
        fields = "__all__"


class QRWalletSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = QRWalletSetting
        fields = "__all__"


class LandingBenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandingBenefit
        fields = ("id", "title", "body", "icon_key", "sort_order")


class LandingGalleryItemSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = LandingGalleryItem
        fields = ("id", "title", "image_url", "sort_order")

    def get_image_url(self, obj: LandingGalleryItem) -> str | None:
        if not obj.image:
            return None
        request = self.context.get("request")
        url = obj.image.url
        if request:
            return request.build_absolute_uri(url)
        return url


class LandingPageSettingsSerializer(serializers.ModelSerializer):
    banner_image_url = serializers.SerializerMethodField()

    class Meta:
        model = LandingPageSettings
        fields = (
            "eyebrow",
            "headline",
            "intro",
            "investment_label",
            "investment_value",
            "income_banner",
            "cta_title",
            "cta_body",
            "slogan",
            "phone",
            "email",
            "website",
            "address",
            "banner_image_url",
            "is_active",
        )

    def get_banner_image_url(self, obj: LandingPageSettings) -> str | None:
        if not obj.banner_image:
            return None
        request = self.context.get("request")
        url = obj.banner_image.url
        if request:
            return request.build_absolute_uri(url)
        return url


class KnowledgeItemSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    audience_label = serializers.CharField(source="get_audience_display", read_only=True)
    media_type_label = serializers.CharField(source="get_media_type_display", read_only=True)

    class Meta:
        model = KnowledgeItem
        fields = (
            "id",
            "title",
            "body",
            "audience",
            "audience_label",
            "media_type",
            "media_type_label",
            "file",
            "file_url",
            "video_url",
            "sort_order",
            "is_published",
            "created_at",
        )
        extra_kwargs = {
            "file": {"write_only": True, "required": False},
            "is_published": {"required": False},
        }

    def create(self, validated_data):
        validated_data.setdefault("is_published", True)
        return super().create(validated_data)

    def get_file_url(self, obj):
        return absolute_media_url(
            obj.file, self.context.get("request"), version=getattr(obj, "updated_at", None)
        )
