from django.db import models
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import MoneyField


class PaymentTransactionMixin(models.Model):
    INITIATED = "Initiated"
    PENDING = "Pending"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"

    STATUS_CHOICES = (
        (INITIATED.lower(), _(INITIATED)),
        (PENDING.lower(), _(PENDING)),
        (COMPLETED.lower(), _(COMPLETED)),
        (FAILED.lower(), _(FAILED)),
        (CANCELLED.lower(), _(CANCELLED)),
    )

    quantity = models.PositiveIntegerField(default=1, verbose_name=_("quantity"))
    amount = MoneyField(
        max_digits=14,
        decimal_places=2,
        default=0,
        default_currency="NGN",
        blank=False,
        null=False,
    )  # type: ignore
    transaction_reference = models.CharField(
        blank=True, null=True, max_length=255, verbose_name=_("transaction reference")
    )
    paid = models.BooleanField(default=False, verbose_name=_("paid"))
    status = models.CharField(
        max_length=255,
        choices=STATUS_CHOICES,
        default=INITIATED.lower(),
        verbose_name=_("status"),
    )

    class Meta:
        abstract = True
