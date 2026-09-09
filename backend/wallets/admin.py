from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet
from unfold.admin import ModelAdmin

from wallets.models import FundTransferRequest, LedgerEntry, Wallet
from wallets.purge import WalletPurgeError, purge_wallet


def _live_by_default(qs: QuerySet, request, *, param: str = "is_deleted") -> QuerySet:
    """Hide soft-deleted rows unless admin explicitly filters Is deleted = Yes."""
    raw = request.GET.get(f"{param}__exact")
    if raw == "1":
        return qs.filter(is_deleted=True)
    if raw == "0":
        return qs.filter(is_deleted=False)
    return qs.filter(is_deleted=False)


@admin.register(Wallet)
class WalletAdmin(ModelAdmin):
    list_display = ("associate", "wallet_type", "balance", "held_balance", "currency", "is_deleted")
    list_filter = ("wallet_type", "is_deleted")
    search_fields = ("associate__associate_id",)
    list_filter_submit = True
    actions = ("purge_selected_wallets", "permanently_destroy_wallets")

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def get_queryset(self, request):
        qs = Wallet.all_objects.select_related("associate")
        return _live_by_default(qs, request)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_staff or request.user.is_superuser)

    def get_deleted_objects(self, objs, request):
        objs = list(objs)
        to_delete = [
            (
                f"{obj} → archive wallet + {obj.entries.count()} ledger row(s) "
                f"(balance zeroed; PROTECT bypass)"
            )
            for obj in objs
        ]
        return to_delete, {Wallet._meta.verbose_name_plural: len(objs)}, set(), []

    def delete_model(self, request, obj):
        try:
            result = purge_wallet(wallet=obj, hard=False)
        except WalletPurgeError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
            raise PermissionDenied(str(exc)) from exc
        self.message_user(
            request,
            (
                f"Archived {result['associate_id']}:{result['wallet_type']} wallet "
                f"({result['ledger_removed']} ledger row(s); balance zeroed)."
            ),
            level=messages.SUCCESS,
        )

    def delete_queryset(self, request, queryset):
        ok = 0
        for obj in queryset:
            try:
                purge_wallet(wallet=obj, hard=False)
                ok += 1
            except WalletPurgeError as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
        if ok:
            self.message_user(
                request,
                f"Archived {ok} wallet(s) and their ledger entries.",
                level=messages.SUCCESS,
            )

    @admin.action(description="Archive wallet + ledger entries (zero balance)")
    def purge_selected_wallets(self, request, queryset):
        self.delete_queryset(request, queryset)

    @admin.action(description="Permanently destroy wallet + ledger (superuser)")
    def permanently_destroy_wallets(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Only superusers can permanently destroy.", level=messages.ERROR)
            return
        ok = 0
        for obj in queryset:
            try:
                purge_wallet(wallet=obj, hard=True)
                ok += 1
            except WalletPurgeError as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
        if ok:
            self.message_user(
                request,
                f"Permanently destroyed {ok} wallet(s) and ledger rows.",
                level=messages.WARNING,
            )


@admin.register(LedgerEntry)
class LedgerEntryAdmin(ModelAdmin):
    list_display = ("wallet", "entry_type", "amount", "balance_after", "reference", "created_at", "is_deleted")
    list_filter = ("entry_type", "is_deleted")
    search_fields = ("reference", "narration", "wallet__associate__associate_id")
    list_filter_submit = True
    actions = ("archive_selected_ledger_entries", "permanently_destroy_ledger_entries")

    def get_queryset(self, request):
        qs = LedgerEntry.all_objects.select_related("wallet", "wallet__associate")
        return _live_by_default(qs, request)

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Default bulk delete says "deleted" but we soft-archive — use explicit actions.
        actions.pop("delete_selected", None)
        return actions

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_staff or request.user.is_superuser)

    def get_deleted_objects(self, objs, request):
        objs = list(objs)
        to_delete = [f"{obj} → archive (hidden from list; filter Is deleted = Yes to view)" for obj in objs]
        return to_delete, {LedgerEntry._meta.verbose_name_plural: len(objs)}, set(), []

    def delete_model(self, request, obj):
        if obj.is_deleted:
            self.message_user(request, "Already archived.", level=messages.WARNING)
            return
        obj.delete(soft=True)
        self.message_user(
            request,
            f"Archived ledger entry {obj.reference or obj.pk} (hidden from live list).",
            level=messages.SUCCESS,
        )

    def delete_queryset(self, request, queryset):
        count = queryset.filter(is_deleted=False).count()
        if count:
            queryset.filter(is_deleted=False).delete(soft=True)
        self.message_user(
            request,
            f"Archived {count} ledger row(s). Hidden from this list — filter Is deleted = Yes to review.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Archive selected (hide from list)")
    def archive_selected_ledger_entries(self, request, queryset):
        self.delete_queryset(request, queryset)

    @admin.action(description="Permanently destroy selected (superuser)")
    def permanently_destroy_ledger_entries(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Only superusers can permanently destroy.", level=messages.ERROR)
            return
        count = queryset.count()
        queryset.delete(force=True)
        self.message_user(
            request,
            f"Permanently destroyed {count} ledger row(s).",
            level=messages.WARNING,
        )


@admin.register(FundTransferRequest)
class FundTransferRequestAdmin(ModelAdmin):
    list_display = (
        "requester",
        "beneficiary",
        "amount",
        "payment_method",
        "utr",
        "status",
        "reviewed_by",
        "created_at",
    )
    list_filter = ("status", "payment_method")
    search_fields = (
        "requester__associate_id",
        "beneficiary__associate_id",
        "note",
        "utr",
    )
    raw_id_fields = ("requester", "beneficiary", "reviewed_by", "ledger_entry")
    readonly_fields = ("reviewed_at", "ledger_entry")
    fields = (
        "requester",
        "beneficiary",
        "amount",
        "wallet_type",
        "payment_method",
        "utr",
        "proof",
        "note",
        "status",
        "rejection_reason",
        "reviewed_by",
        "reviewed_at",
        "ledger_entry",
        "apply_business",
    )
    list_filter_submit = True

    def has_module_permission(self, request):
        return bool(request.user.is_staff or request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        user = request.user
        if user.is_superuser:
            return True
        return bool(
            user.is_staff
            and (
                user.has_perm("wallets.can_fund_transfer")
                or user.has_perm("wallets.change_fundtransferrequest")
            )
        )
