from django.contrib import admin
from unfold.admin import ModelAdmin

from cms.models import (
    HelpTicket,
    KnowledgeItem,
    LandingBenefit,
    LandingGalleryItem,
    LandingPageSettings,
    NewsItem,
    QRWalletSetting,
)


@admin.register(NewsItem)
class NewsItemAdmin(ModelAdmin):
    list_display = ("title", "is_published", "published_at", "created_at")
    list_filter = ("is_published",)
    search_fields = ("title", "body")


@admin.register(HelpTicket)
class HelpTicketAdmin(ModelAdmin):
    list_display = ("subject", "email", "status", "associate_id", "created_at")
    list_filter = ("status",)
    search_fields = ("subject", "body", "email", "associate_id")


@admin.register(QRWalletSetting)
class QRWalletSettingAdmin(ModelAdmin):
    list_display = ("label", "wallet_address", "is_active", "created_at")
    list_filter = ("is_active",)


@admin.register(LandingPageSettings)
class LandingPageSettingsAdmin(ModelAdmin):
    list_display = ("headline", "phone", "email", "is_active", "updated_at")
    list_filter = ("is_active",)
    fieldsets = (
        (
            "Partner section content",
            {"fields": ("eyebrow", "headline", "intro", "is_active")},
        ),
        (
            "Investment highlight",
            {"fields": ("investment_label", "investment_value", "income_banner")},
        ),
        (
            "CTA & slogan",
            {"fields": ("cta_title", "cta_body", "slogan")},
        ),
        (
            "Contact (footer strip)",
            {"fields": ("phone", "email", "website", "address")},
        ),
        (
            "Banner image",
            {
                "description": "Optional wide image under the partner intro. Recommended 1200×675, under 800 KB.",
                "fields": ("banner_image",),
            },
        ),
    )


@admin.register(LandingBenefit)
class LandingBenefitAdmin(ModelAdmin):
    list_display = ("title", "icon_key", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active", "icon_key")
    list_filter = ("is_active",)
    search_fields = ("title", "body")
    ordering = ("sort_order",)


@admin.register(LandingGalleryItem)
class LandingGalleryItemAdmin(ModelAdmin):
    list_display = ("title", "sort_order", "is_active", "has_image")
    list_editable = ("sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title",)
    ordering = ("sort_order",)

    @admin.display(boolean=True, description="Image")
    def has_image(self, obj):
        return bool(obj.image)


@admin.register(KnowledgeItem)
class KnowledgeItemAdmin(ModelAdmin):
    list_display = ("title", "audience", "media_type", "is_published", "sort_order", "created_at")
    list_filter = ("audience", "media_type", "is_published")
    list_editable = ("sort_order", "is_published")
    search_fields = ("title", "body")
    ordering = ("sort_order", "-created_at")
