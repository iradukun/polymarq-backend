import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from polymarq_backend.core.mixins import CreatedAndUpdatedAtMixin


class Notification(CreatedAndUpdatedAtMixin, models.Model):
    JOB = "JOB"
    TOOL_NEGOTIATION = "TOOL-NEGOTIATION"
    TOOL_NEGOTIATION_RESPONSE = "TOOL-NEGOTIATION-RESPONSE"
    TOOL_RENTAL = "TOOL-RENTAL"
    MAINTENANCE = "MAINTENANCE"
    PAYMENT = "PAYMENT"
    ACCOUNT = "ACCOUNT"
    OTHER = "OTHER"

    NOTIFICATION_TYPES = (
        (JOB, JOB),
        (TOOL_NEGOTIATION, TOOL_NEGOTIATION),
        (TOOL_NEGOTIATION_RESPONSE, TOOL_NEGOTIATION_RESPONSE),
        (TOOL_RENTAL, TOOL_RENTAL),
        (MAINTENANCE, MAINTENANCE),
        (PAYMENT, PAYMENT),
        (ACCOUNT, ACCOUNT),
        (OTHER, OTHER),
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    title = models.CharField(verbose_name=_("notification's title"), max_length=256)
    body = models.TextField(verbose_name=_("notification's body"))
    payload = models.JSONField(verbose_name=_("notification's payload"), null=True)
    is_read = models.BooleanField(default=False)
    notification_type = models.CharField(
        verbose_name=_("notification's type"),
        choices=NOTIFICATION_TYPES,
        default=OTHER,
        null=True,
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("notification's recipient (user)"),
    )
    is_deleted = models.BooleanField(default=False)
