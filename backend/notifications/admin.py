from django.contrib import admin
from unfold.admin import ModelAdmin

from notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ("title", "user", "channel", "is_read", "created_at")
    list_filter = ("channel", "is_read")
    search_fields = ("title", "user__email")
    list_filter_submit = True
