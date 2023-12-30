from datetime import datetime

import timeago
from django.utils.timezone import get_default_timezone, make_aware
from rest_framework import serializers

from polymarq_backend.apps.notifications.models import Notification

timezone = get_default_timezone()


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"


class NotificationReadSerializer(serializers.ModelSerializer):
    created_display = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "uuid",
            "title",
            "body",
            "is_read",
            "payload",
            "created_at",
            "created_display",
            "notification_type",
        )

    def get_created_display(self, obj: Notification):
        return timeago.format(obj.created_at, make_aware(datetime.now(), timezone))


class NotificationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("is_read",)


class NotificationCountSerializer(serializers.Serializer):
    data = NotificationReadSerializer(many=True)  # type: ignore
    count = serializers.IntegerField()
    unread_count = serializers.IntegerField()
