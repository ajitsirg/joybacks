from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display

from operations.models import DepositRequest, KYCSubmission, WithdrawalRequest


@admin.register(KYCSubmission)
class KYCAdmin(ModelAdmin):
    list_display = (
        "associate",
        "full_name",
        "display_status",
        "aadhaar_ok",
        "created_at",
        "reviewed_at",
    )
    list_filter = ("status",)
    search_fields = ("associate__associate_id", "pan", "full_name", "aadhaar")
    list_filter_submit = True
    readonly_fields = ("created_at", "reviewed_at", "aadhaar_ok")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "associate",
                    "full_name",
                    "pan",
                    "aadhaar",
                    "bank_name",
                    "account_number",
                    "ifsc",
                    "upi_id",
                    "status",
                    "rejection_reason",
                )
            },
        ),
        (
            "Photos & documents",
            {
                "description": "Aadhaar is attached only when both front and back are uploaded.",
                "fields": (
                    "profile_photo",
                    "aadhaar_document",
                    "aadhaar_back",
                    "aadhaar_ok",
                    "pan_document",
                    "bank_document",
                ),
            },
        ),
        ("Review", {"fields": ("reviewed_by", "reviewed_at", "created_at")}),
    )

    @display(
        description="Status",
        label={
            "pending": "warning",
            "approved": "success",
            "rejected": "danger",
        },
    )
    def display_status(self, obj):
        return obj.status

    @display(description="Aadhaar attached", boolean=True)
    def aadhaar_ok(self, obj):
        return bool(obj.aadhaar_attached)


@admin.register(DepositRequest)
class DepositAdmin(ModelAdmin):
    list_display = ("associate", "amount", "wallet_type", "display_status", "created_at")
    list_filter = ("status", "wallet_type")
    search_fields = ("associate__associate_id",)
    list_filter_submit = True

    @display(
        description="Status",
        label={
            "pending": "warning",
            "approved": "success",
            "completed": "success",
            "rejected": "danger",
        },
    )
    def display_status(self, obj):
        return obj.status


@admin.register(WithdrawalRequest)
class WithdrawalAdmin(ModelAdmin):
    list_display = (
        "associate",
        "amount",
        "net_amount",
        "display_status",
        "requires_maker_checker",
        "created_at",
    )
    list_filter = ("status", "requires_maker_checker")
    search_fields = ("associate__associate_id",)
    list_filter_submit = True

    @display(
        description="Status",
        label={
            "pending": "warning",
            "approved": "success",
            "completed": "success",
            "rejected": "danger",
            "processing": "info",
        },
    )
    def display_status(self, obj):
        return obj.status
