from django.contrib import admin

from polymarq_backend.apps.maintenance import models


@admin.register(models.Maintenance)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "frequency",
        "name",
    )
    readonly_fields = ("uuid", "created_at", "updated_at")
