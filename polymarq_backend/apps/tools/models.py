import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import MoneyField

from polymarq_backend.apps.users.models import Technician, User
from polymarq_backend.core.mixins import CreatedAndUpdatedAtMixin


class ToolCategory(CreatedAndUpdatedAtMixin, models.Model):
    """
    Tools Category Model for Polymarq Backend,
    to categorize technicians'/engineers' tools in the market place
    """

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256, unique=True, verbose_name=_("category name"))
    description = models.TextField(
        max_length=800,
        default=str,
        verbose_name=_("category description"),
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=False,
        null=True,
        related_name="tool_categories_created",
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Tool Category")
        verbose_name_plural = _("Tool Categories")


# create a model for tools images
class ToolImage(CreatedAndUpdatedAtMixin, models.Model):
    """
    Tools images for Polymarq technicians for rent
    """

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    image = models.ImageField(
        upload_to="tools/images",
        verbose_name=_("tool's image"),
        blank=False,
        null=False,
    )
    is_deleted = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        Technician,
        on_delete=models.SET_NULL,
        blank=False,
        null=True,
        related_name="tool_images_created",
    )

    def __str__(self):
        return self.image.name

    class Meta:
        verbose_name = _("Tool Image")
        verbose_name_plural = _("Tool Images")


class Tool(CreatedAndUpdatedAtMixin, models.Model):
    """
    Tools for Polymarq technicians for rent
    """

    # "new", "used-like new","used -very good","used-good", "used:worn"
    CONDITION_NEW = "NEW"
    CONDITION_USED_LIKE_NEW = "USED: LIKE-NEW"
    CONDITION_USED_VERY_GOOD = "USED: VERY GOOD"
    CONDITION_USED_GOOD = "USED: GOOD"
    CONDITION_USED_WORN = "USED: WORN"

    TOOL_CONDITIONS = (
        (CONDITION_NEW.lower(), CONDITION_NEW),
        (CONDITION_USED_LIKE_NEW.lower(), CONDITION_USED_LIKE_NEW),
        (CONDITION_USED_VERY_GOOD.lower(), CONDITION_USED_VERY_GOOD),
        (CONDITION_USED_GOOD.lower(), CONDITION_USED_GOOD),
        (CONDITION_USED_WORN.lower(), CONDITION_USED_WORN),
    )

    class PricingPeriods(models.TextChoices):
        HOUR = ("hourly", "HOURLY")
        DAILY = ("daily", "DAILY")

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256, verbose_name=_("tool's name"))
    category = models.ForeignKey(
        ToolCategory,
        verbose_name=_("tool's category"),
        related_name="tools",
        on_delete=models.CASCADE,
    )
    description = models.TextField(
        max_length=800,
        default=str,
        verbose_name=_("tool's description"),
        blank=True,
        null=True,
    )
    # create an image field to allow upload of one or more images
    images = models.ManyToManyField(
        ToolImage,
        verbose_name=_("tool's images"),
        related_name="tools",
        blank=True,
    )
    negotiable = models.BooleanField(default=False)  # a field that defines is the item is negotiable or otherwise
    owner = models.ForeignKey(
        Technician,
        on_delete=models.SET_NULL,
        related_name="tools_created",
        verbose_name=_("tools' owner"),
        blank=False,
        null=True,
    )
    pricing_period = models.CharField(choices=PricingPeriods.choices, default=PricingPeriods.HOUR)
    price = MoneyField(
        max_digits=14,
        decimal_places=2,
        default=0,
        default_currency="NGN",
        verbose_name=_("tool's price"),
        blank=False,
        null=False,
    )  # type: ignore
    condition = models.CharField(
        choices=TOOL_CONDITIONS,
        default=CONDITION_NEW,
        verbose_name=_("tool's condition"),
        blank=False,
    )
    quantity = models.IntegerField(
        default=1, verbose_name=_("tool's quantity")
    )  # quantity of tools available for rent/purchase

    # CharField to store comma-separated color codes
    color_codes = models.CharField(max_length=255, blank=True, null=True)

    is_rented = models.BooleanField(default=False)  # a field that defines a tool rented or otherwise
    is_available = models.BooleanField(default=True)  # a field that determines if a tool is available for rent
    is_deleted = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Tool")
        verbose_name_plural = _("Tools")

    def __str__(self):
        return self.name

    def set_color_codes(self, color_codes):
        # Convert the list of color codes to a string and save
        self.color_codes = ",".join(color_codes)
        self.save(update_fields=["color_codes"])

    def get_color_codes(self):
        # Retrieve the stored color codes as a list
        return self.color_codes.split(",") if self.color_codes else []


class ToolNegotiation(CreatedAndUpdatedAtMixin, models.Model):
    """
    Tool Negotiation for shop tools
    """

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PENDING = "pending"

    STATUS_CHOICES = (
        (ACCEPTED.lower(), ACCEPTED),
        (REJECTED.lower(), REJECTED),
        (PENDING.lower(), PENDING),
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    tool = models.ForeignKey(
        Tool,
        verbose_name=_("tool"),
        related_name="negotiations",
        on_delete=models.CASCADE,
    )
    tool_owner = models.ForeignKey(
        Technician,
        verbose_name=_("tool owner"),
        on_delete=models.SET_NULL,
        related_name="negotiations",
        blank=False,
        null=True,
    )
    negotiator = models.ForeignKey(
        User,
        verbose_name=_("negotiator"),
        on_delete=models.SET_NULL,
        related_name="negotiations",
        blank=False,
        null=True,
        help_text="The user (client/technician) who is negotiating the tool",
    )
    offered_price = MoneyField(
        max_digits=14,
        decimal_places=2,
        default=0,
        default_currency="NGN",
        verbose_name=_("offered price"),
        blank=True,
        null=True,
    )  # type: ignore
    status = models.CharField(
        choices=STATUS_CHOICES,
        default=PENDING,
        verbose_name=_("status"),
        blank=False,
    )
    attempts = models.IntegerField(default=0, verbose_name=_("attempts"))

    def __str__(self):
        return self.tool.name


class RentalRequest(CreatedAndUpdatedAtMixin, models.Model):
    """
    Rental request for shop tools
    """

    class RequestStatus(models.TextChoices):
        ACCEPTED = ("accepted", "ACCEPTED")
        REJECTED = ("rejected", "REJECTED")
        PENDING = ("pending", "PENDING")

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    tool = models.ForeignKey(
        Tool,
        verbose_name=_("tool requested"),
        related_name="rental_requests",
        on_delete=models.CASCADE,
    )
    request_owner = models.ForeignKey(
        Technician,
        verbose_name=_("request owner"),
        on_delete=models.SET_NULL,
        related_name="rental_requests",
        blank=False,
        null=True,
    )
    rental_duration = models.IntegerField(
        default=1, verbose_name=_("rental duration")
    )  # rental duration base on the tool's pricing period
    price = MoneyField(
        max_digits=14,
        decimal_places=2,
        default=0,
        default_currency="NGN",
        verbose_name=_("negotiation price"),
        blank=True,
        null=True,
    )  # type: ignore
    request_status = models.CharField(
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING,
        verbose_name=_("request status"),
        blank=False,
    )
    request_status = models.CharField(
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING,
        verbose_name=_("request status"),
        blank=False,
    )
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.tool.name
