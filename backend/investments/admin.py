from django.contrib import admin
from unfold.admin import ModelAdmin

from investments.models import InvestmentContract


@admin.register(InvestmentContract)
class InvestmentContractAdmin(ModelAdmin):
    list_display = (
        "associate",
        "principal",
        "monthly_return",
        "months_paid",
        "months_total",
        "status",
        "next_payout_on",
        "source_reference",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("associate__associate_id", "source_reference")
    readonly_fields = ("created_at", "updated_at")
    list_filter_submit = True
