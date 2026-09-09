from django.contrib import admin
from unfold.admin import ModelAdmin

from audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    list_display = ("action", "module", "actor", "object_type", "object_id", "ip_address", "created_at")
    list_filter = ("module", "action")
    search_fields = ("action", "object_id", "actor__email")
    readonly_fields = [f.name for f in AuditLog._meta.fields]
    list_filter_submit = True
