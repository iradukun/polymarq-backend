from django.contrib import admin

from polymarq_backend.apps.tools import models


@admin.register(models.ToolCategory)
class ToolCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
    )
    list_filter = ("created_at",)
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "description")
    list_filter = ("created_at",)
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at", "uuid")


@admin.register(models.ToolImage)
class ToolImageAdmin(admin.ModelAdmin):
    list_display = ("id", "image")
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.RentalRequest)
class RentalRequestAdmin(admin.ModelAdmin):
    list_display = ("uuid", "tool", "price", "rental_duration")
    list_filter = ("created_at",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.ToolNegotiation)
class ToolNegotiationAdmin(admin.ModelAdmin):
    list_display = (
        "uuid",
        "tool",
        "negotiator",
        "offered_price",
        "status",
        "attempts",
    )
    list_filter = ("created_at",)
    readonly_fields = ("created_at", "updated_at")
