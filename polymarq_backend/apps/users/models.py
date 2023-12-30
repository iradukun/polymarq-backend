import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from polymarq_backend.apps.users.managers import CustomUserManager
from polymarq_backend.core.mixins import CreatedAndUpdatedAtMixin, CreatedAtMixin
from polymarq_backend.core.utils.main import generate_numeric_code


class User(AbstractUser):
    """
    Default custom user model for Polymarq Backend.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    email = models.EmailField(_("email address"), unique=True, blank=True, null=True)
    phone_number = models.CharField(_("phone number"), blank=True, null=True, max_length=20)
    profile_picture = models.ImageField(
        _("profile picture"),
        upload_to="profile_pictures/",
        blank=True,
        null=True,
        help_text=_("The profile picture of the user."),
    )
    longitude = models.FloatField(_("longitude"), blank=True, null=True)
    latitude = models.FloatField(_("latitude"), blank=True, null=True)
    is_technician = models.BooleanField(
        _("technician"),
        default=False,
        help_text=_("Designates whether this user is a technician."),
    )
    is_client = models.BooleanField(
        _("client"),
        default=False,
        help_text=_("Designates whether this user is a client."),
    )
    is_verified = models.BooleanField(
        _("verified"),
        default=False,
        help_text=_("Designates whether this user has verified their accounts."),
    )

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    # use a better name for custom user manager
    user_manager = CustomUserManager()

    def __str__(self):
        return self.username

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})

    @property
    def full_name(self):
        return self.get_full_name()


class VerificationCode(CreatedAtMixin, models.Model):
    """
    Verification code model for Polymarq Backend.
    """

    code = models.CharField(_("code"), max_length=6)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        on_delete=models.CASCADE,
        null=True,
        related_name="verification_codes",
    )
    used = models.BooleanField(_("used"), default=False)
    phone_number = models.CharField(
        _("phone number"),
        max_length=20,
        blank=True,
        null=True,
        help_text=_("The phone number to which the code was sent."),
    )

    # Type hint for the user field
    user: models.ForeignKey[type[User] | None]  # type: ignore # Indicate that the related model is a subclass of User

    def __str__(self):
        return self.code

    class Meta:
        verbose_name = _("verification code")
        verbose_name_plural = _("verification codes")
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        """
        Override the save method to generate a numeric code.
        """
        if not self.code:
            self.code = generate_numeric_code(6)
        super().save(*args, **kwargs)


class TechnicianType(CreatedAndUpdatedAtMixin, models.Model):
    """
    Technician Types model to categorize technicians job titles for Polymarq Backend
    """

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.title


class Technician(CreatedAndUpdatedAtMixin, models.Model):
    """
    Technician model for Polymarq Backend.
    """

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        on_delete=models.CASCADE,
        related_name="technician",
    )
    job_title = models.ForeignKey(
        TechnicianType,
        related_name="technicians",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name=_("job title"),
    )
    professional_summary = models.TextField(max_length=800, default=str, verbose_name=_("professional summary"))
    country = models.CharField(max_length=256, default=str, verbose_name=_("country"))
    city = models.CharField(max_length=256, default=str, verbose_name=_("city"))
    local_government_area = models.CharField(max_length=256, default=str, verbose_name=_("LGA"))
    work_address = models.TextField(max_length=800, default=str, verbose_name=_("work address"))
    services = models.TextField(max_length=800, default=str, verbose_name=_("services offered"))
    years_of_experience = models.IntegerField(default=0, verbose_name=_("years of experience"))
    certificates = models.ManyToManyField(
        "users.TechnicianCertificate",
        related_name="technicians",
        verbose_name=_("certificates"),
    )
    is_deleted = models.BooleanField(default=False, verbose_name=_("is deleted"))

    # Type hint for the user field
    user: models.OneToOneField[type[User]]  # type: ignore # Indicate that the related model is a subclass of User

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name = _("Technician")
        verbose_name_plural = _("Technicians")
        ordering = ["-created_at"]


class TechnicianCertificate(CreatedAndUpdatedAtMixin, models.Model):
    """
    Technician's certificates model for Polymarq Backend.
    """

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    technician = models.ForeignKey(
        Technician,
        related_name="certifications",
        on_delete=models.CASCADE,
        verbose_name=_("technician"),
    )
    file = models.FileField(
        upload_to="technicians-certificate/",
        verbose_name=_("technician certificate"),
        null=True,
        blank=True,
    )
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.technician.user.username


class Client(CreatedAndUpdatedAtMixin, models.Model):
    """
    Client model for Polymarq Backend.
    """

    COMPANY = "Company"
    INDIVIDUAL = "Individual"

    ACCOUNT_TYPE_CHOICES = (
        (COMPANY.lower(), COMPANY),
        (INDIVIDUAL.lower(), INDIVIDUAL),
    )
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        on_delete=models.CASCADE,
        related_name="client",
    )
    account_type = models.CharField(
        _("account type"),
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default=INDIVIDUAL.lower(),
    )
    address = models.TextField(default=str)
    is_deleted = models.BooleanField(default=False)

    # Type hint for the user field
    user: models.OneToOneField[type[User]]  # type: ignore # Indicate that the related model is a subclass of User

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name = _("Client")
        verbose_name_plural = _("Clients")
        ordering = ["-created_at"]
