from typing import cast

from django.urls import reverse

from polymarq_backend.apps.notifications.models import Notification
from polymarq_backend.apps.notifications.tests.factory import BaseTestCase, NotificationFactory
from polymarq_backend.apps.users.models import User


class TestNotificationView(BaseTestCase):
    email = "userNotif@example.com"
    username = "userNotif"
    password = "polymarqCategory33"
    IOS = 0
    ANDROID = 1
    device_token = "testToken"

    @classmethod
    def setUpTestData(cls):
        cls.user = User.user_manager.create_user(
            email=cls.email,
            username=cls.username,
            password=cls.password,
            first_name="John",
            last_name="Doe",
            phone_number="+234800000000",
            longitude=0,
            latitude=0,
            is_verified=True,
            is_technician=True,
            is_active=True,
        )
        # cls.notification = cast(Notification, NotificationFactory())

    def test_notifications_list(self):
        NotificationFactory.create_batch(4)

        url = reverse("notifications:notification-list")
        response = self.client.get(url, headers=self.headers)  # type: ignore
        response_json = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response_json["result"]["data"], list)
        self.assertIsInstance(response_json["result"]["count"], int)
        self.assertIsInstance(response_json["result"]["unreadCount"], int)

    def test_unread_notifications_list(self):
        notif = cast(Notification, NotificationFactory())
        notif.is_read = True
        notif.save()

        url = reverse("notifications:notification-list")
        response = self.client.get(url + "?unread=true", headers=self.headers)  # type: ignore
        response_json = response.json()
        not_valid = lambda ls: bool([i for i in ls if i["uuid"] == notif.uuid])  # noqa: E731

        self.assertEqual(response.status_code, 200)
        self.assertFalse(not_valid(response_json["result"]["data"]))

    def test_notification_update(self):
        notif = cast(Notification, NotificationFactory())
        NotificationFactory.create_batch(4)

        url = reverse("notifications:notification-detail", args=[notif.uuid])
        response = self.client.patch(
            url,
            data={"is_read": True},
            headers=self.headers,  # type: ignore
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 202)
        self.assertTrue(Notification.objects.get(uuid=notif.uuid).is_read)

    def test_notification_delete(self):
        notif = cast(Notification, NotificationFactory())
        url = reverse("notifications:notification-detail", args=[notif.uuid])
        response = self.client.delete(url, headers=self.headers)  # type: ignore

        self.assertEqual(response.status_code, 204)
        self.assertTrue(Notification.objects.get(uuid=notif.uuid).is_deleted)  # type: ignore
