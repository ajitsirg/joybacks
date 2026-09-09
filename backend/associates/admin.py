from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from unfold.admin import ModelAdmin

from associates.models import Associate, DeletedAssociate, RewardAchievement, RewardLegAssignment
from associates.purge import PurgeError, archive_associate, restore_associate


class AssociateAdmin(ModelAdmin):
    list_display = (
        "associate_id",
        "mobile",
        "lead_reference",
        "earning_level_name",
        "performance_level_name",
        "earning_level",
        "performance_level",
        "card_tier",
        "flag_color",
        "join_amount",
        "personal_business",
        "total_business",
        "status",
        "can_view_admin_history",
        "can_view_reward_achievers",
        "direct_count",
        "created_at",
    )
    list_filter = (
        "status",
        "earning_level",
        "performance_level",
        "card_tier",
        "flag_color",
        "kyc_verified",
        "can_view_admin_history",
        "can_view_reward_achievers",
    )
    list_editable = (
        "flag_color",
        "can_view_admin_history",
        "can_view_reward_achievers",
    )
    search_fields = ("associate_id", "referral_code", "user__username", "mobile", "lead_reference")
    raw_id_fields = ("user", "sponsor")
    list_filter_submit = True
    list_fullwidth = True
    actions = ("archive_selected_associates",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "associate_id",
                    "referral_code",
                    "mobile",
                    "sponsor",
                    "sponsor_associate_id",
                    "lead_reference",
                    "status",
                    "card_tier",
                    "flag_color",
                    "join_amount",
                    "kyc_verified",
                )
            },
        ),
        (
            "Business & rank levels",
            {
                "description": (
                    "Reward / Growth levels sync when you save. "
                    "Delete moves the account to Recycle Bin (hidden from app) and "
                    "shifts under-leg to the upper sponsor."
                ),
                "fields": (
                    "personal_business",
                    "total_business",
                    "earning_level",
                    "earning_level_name",
                    "performance_level",
                    "performance_level_name",
                    "direct_count",
                    "direct_active_count",
                ),
            },
        ),
        (
            "App permissions",
            {
                "fields": (
                    "can_view_admin_history",
                    "can_view_reward_achievers",
                    "login_password",
                ),
            },
        ),
    )
    readonly_fields = (
        "earning_level",
        "earning_level_name",
        "performance_level",
        "performance_level_name",
        "direct_count",
        "direct_active_count",
    )

    def get_queryset(self, request):
        # Live associates only — archived rows live in Recycle Bin
        return Associate.objects.all()

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_staff or request.user.is_superuser)

    def get_deleted_objects(self, objs, request):
        objs = list(objs)
        to_delete = [
            f"{obj} → Recycle Bin (under-leg → upper sponsor; wallets/points archived)"
            for obj in objs
        ]
        return to_delete, {Associate._meta.verbose_name_plural: len(objs)}, set(), []

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Keep rank / growth calculations in sync after admin edits
        obj.sync_flag_color(save=False)
        obj.sync_rank_levels(save=False)
        obj.direct_count = obj.directs.filter(is_deleted=False).count()
        obj.direct_active_count = obj.directs.filter(
            status=Associate.Status.ACTIVE, is_deleted=False
        ).count()
        obj.save(
            update_fields=[
                "flag_color",
                "earning_level",
                "earning_level_name",
                "performance_level",
                "performance_level_name",
                "direct_count",
                "direct_active_count",
                "updated_at",
            ]
        )

    def delete_model(self, request, obj):
        try:
            result = archive_associate(associate=obj)
        except PurgeError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
            raise PermissionDenied(str(exc)) from exc
        self.message_user(
            request,
            (
                f"Moved {result['associate_id']} to Deleted accounts bucket. "
                f"Under-leg → {result['reparent_to'] or 'n/a'} "
                f"({result['reparented']} directs). Hidden from frontend."
            ),
            level=messages.SUCCESS,
        )

    def delete_queryset(self, request, queryset):
        ok = 0
        for obj in queryset:
            try:
                archive_associate(associate=obj)
                ok += 1
            except PurgeError as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
        if ok:
            self.message_user(
                request,
                f"Moved {ok} associate(s) to Deleted / deactivated accounts bucket.",
                level=messages.SUCCESS,
            )

    @admin.action(description="Move to Deleted bucket (hide from app, keep data)")
    def archive_selected_associates(self, request, queryset):
        self.delete_queryset(request, queryset)


@admin.register(DeletedAssociate)
class DeletedAssociateAdmin(ModelAdmin):
    """Recycle Bin: deleted / deactivated accounts with archived related data."""

    list_display = (
        "associate_id",
        "mobile",
        "status",
        "user_active",
        "personal_business",
        "total_business",
        "deleted_at",
        "created_at",
    )
    list_filter = ("status", "deleted_at", "card_tier")
    search_fields = ("associate_id", "mobile", "user__email", "user__username", "referral_code")
    readonly_fields = (
        "user",
        "associate_id",
        "referral_code",
        "mobile",
        "sponsor",
        "sponsor_associate_id",
        "status",
        "personal_business",
        "total_business",
        "join_amount",
        "earning_level",
        "earning_level_name",
        "performance_level",
        "performance_level_name",
        "is_deleted",
        "deleted_at",
        "created_at",
        "updated_at",
    )
    actions = ("restore_selected", "permanently_destroy_selected")
    list_fullwidth = True
    list_filter_submit = True

    @admin.display(boolean=True, description="Login active")
    def user_active(self, obj):
        return bool(obj.user_id and obj.user.is_active)

    def get_queryset(self, request):
        # Deleted associates + deactivated logins still marked alive
        return (
            DeletedAssociate.all_objects.filter(
                Q(is_deleted=True) | Q(user__is_active=False)
            )
            .select_related("user", "sponsor")
            .distinct()
        )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

    def get_deleted_objects(self, objs, request):
        objs = list(objs)
        to_delete = [f"{obj} (PERMANENT destroy — cannot undo)" for obj in objs]
        return to_delete, {"accounts": len(objs)}, set(), []

    def delete_model(self, request, obj):
        try:
            result = archive_associate(associate=obj, hard=True)
        except PurgeError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
            raise PermissionDenied(str(exc)) from exc
        self.message_user(
            request,
            f"Permanently destroyed {result['associate_id']} and related data.",
            level=messages.WARNING,
        )

    def delete_queryset(self, request, queryset):
        ok = 0
        for obj in queryset:
            try:
                archive_associate(associate=obj, hard=True)
                ok += 1
            except PurgeError as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
        if ok:
            self.message_user(request, f"Permanently destroyed {ok} account(s).", level=messages.WARNING)

    @admin.action(description="Restore to live app (inactive)")
    def restore_selected(self, request, queryset):
        ok = 0
        for obj in queryset:
            try:
                restore_associate(associate=obj)
                ok += 1
            except PurgeError as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
        if ok:
            self.message_user(request, f"Restored {ok} account(s) to live associates.", level=messages.SUCCESS)

    @admin.action(description="Permanently destroy selected (superuser)")
    def permanently_destroy_selected(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Only superusers can permanently destroy.", level=messages.ERROR)
            return
        self.delete_queryset(request, queryset)


@admin.register(RewardLegAssignment)
class RewardLegAssignmentAdmin(ModelAdmin):
    list_display = ("owner", "slot", "performer", "locked", "updated_at")
    list_filter = ("slot", "locked")
    search_fields = ("owner__associate_id", "performer__associate_id")
    raw_id_fields = ("owner", "performer")


@admin.register(RewardAchievement)
class RewardAchievementAdmin(ModelAdmin):
    list_display = (
        "associate",
        "milestone",
        "reward_amount",
        "total_business",
        "leg1_business",
        "leg2_business",
        "leg3_business",
        "status",
        "credited_at",
        "reference",
    )
    list_filter = ("status", "milestone")
    search_fields = ("associate__associate_id", "reference")
    raw_id_fields = ("associate",)
    readonly_fields = ("qualified_at", "credited_at", "reference")


# Register live associates (explicit so proxy registration order is clear)
admin.site.register(Associate, AssociateAdmin)
