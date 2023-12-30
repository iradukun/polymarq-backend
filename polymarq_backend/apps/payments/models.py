import uuid

from django.core.validators import MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import MoneyField

from polymarq_backend.apps.jobs.models import Job
from polymarq_backend.apps.payments.mixins import PaymentTransactionMixin
from polymarq_backend.apps.tools.models import Tool
from polymarq_backend.apps.users.models import Client, Technician, User
from polymarq_backend.core.mixins import CreatedAndUpdatedAtMixin


class JobPriceQuotation(CreatedAndUpdatedAtMixin, models.Model):
    """
    Job Price Quotation model for Polymarq Backend.
    Should store values of uniformed sampled price quotations only.
    """

    job = models.ForeignKey(
        Job,
        verbose_name=_("job"),
        on_delete=models.CASCADE,
        related_name="price_quotations",
    )
    technician = models.ForeignKey(
        Technician,
        verbose_name=_("technician"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="price_quotations",
    )
    price = MoneyField(
        max_digits=14,
        decimal_places=2,
        default=0,
        default_currency="NGN",
        blank=False,
        null=False,
    )  # type: ignore
    is_accepted = models.BooleanField(verbose_name=_("is accepted"), default=False)

    class Meta:
        verbose_name = _("Job Price Quotation")
        verbose_name_plural = _("Job Price Quotations")
        constraints = [
            models.UniqueConstraint(
                fields=["technician", "job"],
                name="unique_technician_job_price_quotation",
            )
        ]

    def __str__(self):
        return f"{self.job.name} - {self.technician.user.username}"  # type: ignore


class JobIncrementalPayment(CreatedAndUpdatedAtMixin, PaymentTransactionMixin, models.Model):
    """
    An Incremental payment for Polymarq jobs
    """

    uuid = models.UUIDField(editable=False, default=uuid.uuid4)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="incremental_payments")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="job_incremental_payments")
    technician = models.ForeignKey(Technician, on_delete=models.CASCADE, related_name="job_incremental_payments")
    client_state = models.DecimalField(
        max_digits=5,
        default=0.0,  # type: ignore
        decimal_places=2,
        verbose_name=_("client state"),
        validators=[MaxValueValidator(10.00)],
    )  # type: ignore
    technician_state = models.DecimalField(
        max_digits=5,
        default=0.0,  # type: ignore
        decimal_places=2,
        verbose_name=_("technician state"),
        validators=[MaxValueValidator(10.00)],
    )  # type: ignore


class Bank(CreatedAndUpdatedAtMixin, models.Model):
    name = models.CharField(max_length=255, verbose_name=_("name"))
    slug = models.SlugField(max_length=255, verbose_name=_("slug"))
    code = models.CharField(max_length=255, verbose_name=_("code"))
    longcode = models.CharField(max_length=255, verbose_name=_("longcode"))
    gateway = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("gateway"))
    pay_with_bank = models.BooleanField(default=False, verbose_name=_("pay with bank"))
    active = models.BooleanField(default=True, verbose_name=_("active"))
    country = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("country"))
    currency = models.CharField(max_length=3, default="NGN", null=True, blank=True, verbose_name=_("currency"))

    def __str__(self):
        return self.name


class TechnicianBankAccount(CreatedAndUpdatedAtMixin, models.Model):
    """
    A model for bank details of a Polymarq technician, storing
    bank and paystack details.
    """

    technician = models.OneToOneField(
        Technician,
        verbose_name=_("technician"),
        on_delete=models.CASCADE,
        related_name="technician_bank_account",
    )
    bank = models.ForeignKey(
        Bank,
        verbose_name=_("bank"),
        on_delete=models.CASCADE,
        related_name="technician_bank_accounts",
    )
    account_name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("account name"))
    account_number = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("account number"))
    routing_number = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("routing number"))
    account_type = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("account type"))
    paystack_recipient_code = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("paystack recipient code")
    )
    paystack_subaccount_code = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("paystack subaccount code")
    )

    class Meta:
        verbose_name = _("Technician Bank Account")
        verbose_name_plural = _("Technician Bank Accounts")

    def __str__(self):
        return f"{self.technician.user.username} - {self.bank.name}"


class ToolPurchase(CreatedAndUpdatedAtMixin, PaymentTransactionMixin, models.Model):
    """
    A model for storing tool purchases
    """

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    tool = models.ForeignKey(
        Tool,
        verbose_name=_("tool"),
        on_delete=models.CASCADE,
        related_name="tool_purchases",
    )
    seller = models.ForeignKey(
        Technician,
        verbose_name=_("technician"),
        on_delete=models.CASCADE,
        null=True,
        related_name="tool_purchases",
        help_text="The technician who sold the tool",
    )
    buyer = models.ForeignKey(
        User,
        verbose_name=_("buyer user"),
        on_delete=models.CASCADE,
        null=True,
        related_name="tool_purchases",
        help_text="The user (client/technician) who bought the tool",
    )

    class Meta:
        verbose_name = _("Tool Purchase")
        verbose_name_plural = _("Tool Purchases")

    def __str__(self):
        return f"{self.tool.name} - {self.technician.user.username}"  # type: ignore


class JobInitialPayment(CreatedAndUpdatedAtMixin, PaymentTransactionMixin, models.Model):
    """
    An initial payment for Polymarq jobs
    """

    uuid = models.UUIDField(editable=False, default=uuid.uuid4)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="job_initial_payments")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="job_initial_payments")
    technician = models.ForeignKey(Technician, on_delete=models.CASCADE, related_name="job_initial_payments")

    class Meta:
        verbose_name = _("Job Initial Payment")
        verbose_name_plural = _("Job Initial Payments")

    def __str__(self):
        return f"{self.job.name} - {self.technician.user.username}"  # type: ignore
