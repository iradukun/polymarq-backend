from django.contrib import admin

from polymarq_backend.apps.payments import models


@admin.register(models.JobPriceQuotation)
class JobPriceQuotationAdmin(admin.ModelAdmin):
    list_display = (
        "job",
        "technician",
        "price",
        "is_accepted",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.JobIncrementalPayment)
class JobIncrementalPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "uuid",
        "job",
        "amount",
        "paid",
    )
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(models.TechnicianBankAccount)
class TechnicianBankAccountAdmin(admin.ModelAdmin):
    list_display = (
        "technician",
        "bank",
        "account_name",
        "account_number",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.Bank)
class BankAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.ToolPurchase)
class ToolPurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "uuid",
        "tool",
        "quantity",
        "amount",
        "transaction_reference",
        "paid",
    )
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(models.JobInitialPayment)
class JobInitialPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "uuid",
        "job",
        "client",
        "technician",
        "transaction_reference",
    )
    readonly_fields = ("uuid", "created_at", "updated_at")
