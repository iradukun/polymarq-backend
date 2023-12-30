from django.test import TestCase

from polymarq_backend.apps.notifications.models import Notification
from polymarq_backend.apps.users.models import User


class TestNotificationModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create Client User
        cls.user = User.user_manager.create_user(
            email="UserClient@gmail.com",
            password="polymarq",
            username="UserClient",
            first_name="James",
            last_name="Peace",
            phone_number="+2348080090070",
            longitude=0,
            latitude=0,
            is_client=True,
            is_verified=True,
        )

    def test_model_fields(self):
        notification = Notification.objects.create(
            title="Job Request",
            body="You've a job request",
            notification_type="JobRequest",
            recipient=self.user,
        )
        self.assertEqual(notification.title, "Job Request")
        self.assertEqual(notification.body, "You've a job request")
        self.assertEqual(notification.notification_type, "JobRequest")
        self.assertEqual(notification.is_deleted, False)
        self.assertEqual(notification.is_read, False)
        self.assertEqual(notification.recipient.pk, self.user.pk)
