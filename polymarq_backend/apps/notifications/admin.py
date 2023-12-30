from django.contrib import admin

from polymarq_backend.apps.notifications import models


@admin.register(models.Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "body",
        "is_read",
    )
    list_filter = ("created_at",)
    search_fields = ("title", "body")
    readonly_fields = ("created_at", "updated_at")
