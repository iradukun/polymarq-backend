import uuid

from django.core.validators import MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import MoneyField

from polymarq_backend.apps.users.models import Client, Technician
from polymarq_backend.core.mixins import CreatedAndUpdatedAtMixin


class Job(CreatedAndUpdatedAtMixin, models.Model):
    """
    Job model for Polymarq Backend.
    To enable Clients create jobs
    """

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    VERIFIED = "VERIFIED"
    CANCELLED = "CANCELLED"
    # APPROVED = "APPROVED"
    # SCHEDULED = "SCHEDULED"

    # REJECTED = "REJECTED"
    # PAID = "PAID"
    # DRAFT = "DRAFT"

    STATUSES = (
        (PENDING, PENDING),
        (IN_PROGRESS, IN_PROGRESS),
        (DONE, DONE),
        (VERIFIED, VERIFIED),
        (CANCELLED, CANCELLED),
    )

    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, verbose_name=_("client"), on_delete=models.CASCADE)
    technician = models.ForeignKey(
        Technician,
        verbose_name=_("technician"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    name = models.CharField(verbose_name=_("name"), blank=False, null=False, max_length=150)
    description = models.CharField(verbose_name=_("description"), blank=False, null=False, max_length=1000)
    image = models.ImageField(upload_to="job_images/", verbose_name=_("image"), null=True, blank=True)
    location_address = models.CharField(verbose_name=_("location address"), blank=False, null=False, max_length=1000)
    status = models.CharField(choices=STATUSES, verbose_name=_("status"), max_length=60, default=PENDING)
    location_longitude = models.FloatField(
        verbose_name=_("location longitude"),
        blank=False,
        null=False,
    )
    location_latitude = models.FloatField(
        verbose_name=_("location latitude"),
        blank=False,
        null=False,
    )
    duration = models.PositiveIntegerField(
        blank=False,
        null=False,
        verbose_name=_("duration"),
        help_text=_("The time period for the job (in days)"),
    )
    min_price = MoneyField(
        max_digits=14,
        decimal_places=2,
        default=0,
        default_currency="NGN",
        blank=False,
        null=False,
    )  # type: ignore
    max_price = MoneyField(
        max_digits=14,
        decimal_places=2,
        default=0,
        default_currency="NGN",
        blank=False,
        null=False,
    )  # type: ignore
    require_technicians_immediately = models.BooleanField(
        verbose_name=_("require technicians immediately"),
        blank=False,
        null=False,
        default=False,
    )
    require_technicians_next_day = models.BooleanField(
        verbose_name=_("require technicians next day"),
        blank=False,
        null=False,
        default=False,
    )
    completion_state = models.DecimalField(
        max_digits=5,
        default=0.0,  # type: ignore
        decimal_places=2,
        verbose_name=_("completion state"),
        validators=[MaxValueValidator(10.00)],
    )  # type: ignore
    is_deleted = models.BooleanField(default=False)
    ping_request_cycle = models.PositiveIntegerField(
        blank=False,
        null=False,
        default=1,
        verbose_name=_("ping request cycle"),
        help_text=_("Helps track the number of cycles this job owner has made job request pings"),
    )

    def get_client_location_longitude(self):
        return self.client.user.longitude

    def get_client_location_latitude(self):
        return self.client.user.latitude

    def increase_ping_request_cycle(self):
        self.ping_request_cycle += 1
        self.save(update_fields=["ping_request_cycle"])

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Job")
        verbose_name_plural = _("Jobs")
        ordering = ["-created_at"]


class Ping(CreatedAndUpdatedAtMixin, models.Model):
    DECLINED = "DECLINED"
    ACCEPTED = "ACCEPTED"
    REQUESTED = "REQUESTED"
    NEGOTIATING = "NEGOTIATING"
    EXPIRED = "EXPIRED"

    STATUSES = (
        (REQUESTED, REQUESTED),
        (DECLINED, DECLINED),
        (ACCEPTED, ACCEPTED),
        (NEGOTIATING, NEGOTIATING),
        (EXPIRED, EXPIRED),
    )

    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    technician = models.ForeignKey(Technician, verbose_name=_("technician"), on_delete=models.CASCADE)
    client = models.ForeignKey(Client, verbose_name=_("client"), on_delete=models.CASCADE)
    distance_from_client = models.FloatField(
        verbose_name=_("distance from client"),
        blank=False,
        null=False,
        help_text=_("Value is in kilometers"),
    )
    job = models.ForeignKey(Job, verbose_name=_("job"), on_delete=models.CASCADE, related_name="pings")
    status = models.CharField(choices=STATUSES, verbose_name=_("status"), max_length=60, default=REQUESTED)
    price_quote = MoneyField(
        max_digits=14,
        decimal_places=2,
        default=0,
        default_currency="NGN",
        blank=False,
        null=False,
    )  # type: ignore
    transaction_cost = MoneyField(
        max_digits=14,
        decimal_places=2,
        default=0,
        default_currency="NGN",
        verbose_name=_("The transaction cost applied to this ping if accepted for a job"),
        blank=True,
        null=True,
    )  # type: ignore

    def __str__(self):
        return f"Ping - {self.job.name}"

    class Meta:
        verbose_name = _("Ping")
        verbose_name_plural = _("Pings")
        ordering = ["-created_at"]
