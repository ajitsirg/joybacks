from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from commissions.models import AdminCharge, CommissionEntry, CommissionRun


class EntryInline(TabularInline):
    model = CommissionEntry
    extra = 0
    readonly_fields = (
        "beneficiary",
        "source_associate",
        "level",
        "percent",
        "sale_amount",
        "amount",
        "wallet_type",
        "reference",
        "status",
        "narration",
    )
    tab = True


@admin.register(CommissionRun)
class CommissionRunAdmin(ModelAdmin):
    list_display = ("run_type", "status", "source_reference", "source_amount", "created_at")
    list_filter = ("run_type", "status")
    inlines = [EntryInline]
    list_filter_submit = True


@admin.register(CommissionEntry)
class CommissionEntryAdmin(ModelAdmin):
    list_display = (
        "beneficiary",
        "source_associate",
        "level",
        "growth_level",
        "percent",
        "sale_amount",
        "monthly_return_amount",
        "month_index",
        "amount",
        "admin_charge_amount",
        "net_amount",
        "reference",
        "status",
        "wallet_type",
        "created_at",
    )
    list_filter = ("wallet_type", "level", "status", "growth_level")
    search_fields = ("beneficiary__associate_id", "source_associate__associate_id", "reference")
    list_filter_submit = True


@admin.register(AdminCharge)
class AdminChargeAdmin(ModelAdmin):
    list_display = (
        "associate",
        "kind",
        "gross_amount",
        "charge_percent",
        "charge_amount",
        "net_amount",
        "reference",
        "created_at",
    )
    list_filter = ("kind", "wallet_type")
    search_fields = ("associate__associate_id", "reference", "narration")
    list_filter_submit = True
    readonly_fields = (
        "associate",
        "kind",
        "wallet_type",
        "gross_amount",
        "charge_percent",
        "charge_amount",
        "net_amount",
        "reference",
        "narration",
        "commission_entry",
        "ledger_entry",
        "created_at",
    )
