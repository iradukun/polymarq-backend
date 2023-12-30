from django.contrib import admin

from polymarq_backend.apps.jobs import models


@admin.register(models.Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "status",
        "name",
    )
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(models.Ping)
class PingAdmin(admin.ModelAdmin):
    list_display = (
        "status",
        "updated_at",
    )
    readonly_fields = ("uuid", "created_at", "updated_at")
