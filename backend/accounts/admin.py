from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.core.exceptions import PermissionDenied
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from accounts.models import DeviceLogin, OTPChallenge, Permission, Role, StaffProfile, User
from associates.purge import PurgeError, archive_associate


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    ordering = ("email",)
    list_display = ("email", "username", "user_type", "is_staff", "is_active")
    list_filter = ("user_type", "is_staff", "is_active", "is_superuser")
    search_fields = ("email", "username", "phone")
    list_filter_submit = True
    actions = ("purge_selected_users",)
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("JoyClub", {"fields": ("phone", "user_type", "must_change_password", "last_login_ip")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "password1", "password2", "user_type"),
            },
        ),
    )

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_staff or request.user.is_superuser)

    def get_deleted_objects(self, objs, request):
        """Bypass PROTECT collector — associate archive moves data to Recycle Bin."""
        objs = list(objs)
        to_delete = []
        for obj in objs:
            assoc = getattr(obj, "associate", None)
            if assoc is not None:
                to_delete.append(
                    f"{obj.email} + associate {assoc.associate_id} "
                    "→ Deleted accounts bucket (hidden from app)"
                )
            else:
                to_delete.append(str(obj))
        model_count = {User._meta.verbose_name_plural: len(objs)}
        return to_delete, model_count, set(), []

    def delete_model(self, request, obj):
        if obj.is_superuser or obj.is_staff:
            self.message_user(
                request,
                "Staff / superuser accounts cannot be deleted from here.",
                level=messages.ERROR,
            )
            raise PermissionDenied("Staff / superuser cannot be deleted")
        assoc = getattr(obj, "associate", None)
        if assoc is not None:
            try:
                result = archive_associate(associate=assoc)
            except PurgeError as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
                raise PermissionDenied(str(exc)) from exc
            self.message_user(
                request,
                (
                    f"Archived {result['associate_id']} to Deleted accounts bucket "
                    f"(login deactivated, under-leg shifted)."
                ),
                level=messages.SUCCESS,
            )
            return
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        self.message_user(request, "User deactivated.", level=messages.SUCCESS)

    def delete_queryset(self, request, queryset):
        ok = 0
        for obj in queryset:
            if obj.is_superuser or obj.is_staff:
                self.message_user(
                    request,
                    f"Skipped staff/superuser {obj.email}",
                    level=messages.WARNING,
                )
                continue
            assoc = getattr(obj, "associate", None)
            if assoc is not None:
                try:
                    archive_associate(associate=assoc)
                    ok += 1
                except PurgeError as exc:
                    self.message_user(request, str(exc), level=messages.ERROR)
            else:
                obj.is_active = False
                obj.save(update_fields=["is_active"])
                ok += 1
        if ok:
            self.message_user(
                request,
                f"Archived/deactivated {ok} user(s). See Deleted / deactivated accounts.",
                level=messages.SUCCESS,
            )

    @admin.action(description="Move to Deleted bucket (hide from app)")
    def purge_selected_users(self, request, queryset):
        self.delete_queryset(request, queryset)


@admin.register(Permission)
class PermissionAdmin(ModelAdmin):
    list_display = ("code", "name", "module")
    list_filter = ("module",)
    search_fields = ("code", "name")
    list_filter_submit = True


@admin.register(Role)
class RoleAdmin(ModelAdmin):
    list_display = ("name", "is_system", "can_fund_transfer", "permission_count", "created_at")
    filter_horizontal = ("permissions",)
    search_fields = ("name",)
    list_filter = ("is_system",)

    @admin.display(boolean=True, description="Fund transfer")
    def can_fund_transfer(self, obj):
        return obj.permissions.filter(code__in=("fund.transfer", "wallets.transfer")).exists()

    @admin.display(description="Permissions")
    def permission_count(self, obj):
        return obj.permissions.count()


@admin.register(StaffProfile)
class StaffProfileAdmin(ModelAdmin):
    list_display = ("employee_code", "user", "department", "is_suspended")
    filter_horizontal = ("roles",)
    search_fields = ("employee_code", "user__email")

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        from accounts.rbac_seed import sync_staff_django_groups

        sync_staff_django_groups(form.instance.user)


@admin.register(DeviceLogin)
class DeviceLoginAdmin(ModelAdmin):
    list_display = ("user", "device_name", "ip_address", "is_active", "last_seen_at")
    search_fields = ("user__email", "device_name", "ip_address")


@admin.register(OTPChallenge)
class OTPChallengeAdmin(ModelAdmin):
    list_display = ("phone_or_email", "purpose", "is_used", "expires_at", "created_at")
    list_filter = ("purpose", "is_used")
    search_fields = ("phone_or_email",)
