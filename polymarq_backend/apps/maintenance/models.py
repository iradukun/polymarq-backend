import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import MoneyField

from polymarq_backend.apps.users.models import Client, Technician, TechnicianType
from polymarq_backend.core.mixins import CreatedAndUpdatedAtMixin


class Maintenance(CreatedAndUpdatedAtMixin, models.Model):
    """
    Maintenance model for Polymarq Backend.
    To enable Clients schedule maintenance services
    """

    MONTHLY = "MONTHLY"
    WEEKLY = "WEEKLY"

    FREQUENCY = ((WEEKLY, WEEKLY), (MONTHLY, MONTHLY))

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
    frequency = models.CharField(choices=FREQUENCY, verbose_name=_("frequency"), max_length=60, default=WEEKLY)
    technician_type = models.ForeignKey(TechnicianType, verbose_name=_("technician type"), on_delete=models.CASCADE)
    name = models.CharField(verbose_name=_("name"), blank=False, null=False, max_length=150)
    description = models.CharField(verbose_name=_("description"), blank=False, null=False, max_length=1000)
    image = models.ImageField(upload_to="maintenance_images/", verbose_name=_("image"), null=True, blank=True)
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
    location_address = models.CharField(verbose_name=_("location address"), blank=False, null=False, max_length=1000)
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
        help_text=_("The time period for the maintenance (in days)"),
    )
    is_deleted = models.BooleanField(default=False)

    def get_client_location_longitude(self):
        return self.client.user.longitude

    def get_client_location_latitude(self):
        return self.client.user.latitude

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Maintenance")
        verbose_name_plural = _("Maintenances")
        ordering = ["-created_at"]
