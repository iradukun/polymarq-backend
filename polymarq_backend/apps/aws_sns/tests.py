import json
from unittest.mock import patch

from django.test import TestCase

from polymarq_backend.apps.aws_sns.models import Device, Log
from polymarq_backend.apps.aws_sns.tasks import (
    deregister_device,
    refresh_device,
    register_device,
    send_sns_mobile_push_notification_to_device,
)
from polymarq_backend.apps.users.models import User


class TestNotificationTasks(TestCase):
    @classmethod
    def setUpClass(cls):
        Device.objects.all().delete()
        Log.objects.all().delete()
        User.user_manager.create_user(
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

    @classmethod
    def tearDownClass(cls):
        Device.objects.all().delete()
        Log.objects.all().delete()
        User.objects.all().delete()

    @patch("polymarq_backend.apps.aws_sns.models.Client")
    def test_register(self, mock_Client):
        Log.objects.all().delete()
        token = "token"
        device = Device.objects.create(token=token, os=Device.ANDROID_OS, arn="arn", user=User.objects.first())

        mock_response = {"EndpointArn": "arn"}
        mock_Client().create_android_platform_endpoint.return_value = mock_response
        response = register_device(device)
        device.refresh_from_db()
        self.assertEqual(response["EndpointArn"], mock_response["EndpointArn"])
        self.assertEqual(device.arn, mock_response["EndpointArn"])

    @patch("polymarq_backend.apps.aws_sns.models.Client")
    def test_refresh_when_enabled(self, mock_Client):
        Log.objects.all().delete()
        token = "token"
        device = Device.objects.create(token=token, os=Device.ANDROID_OS, arn="arn", user=User.objects.first())
        mock_response = {"Enabled": "true", "Token": token}
        mock_Client().retrieve_platform_endpoint_attributs.return_value = mock_response
        mock_Client().delete_platform_endpoint.return_value = ""
        response = refresh_device(device)
        self.assertEqual(response, mock_response)
        self.assertEqual(device.token, mock_response["Token"])

    @patch("polymarq_backend.apps.aws_sns.models.Client")
    def test_refresh_when_disabled(self, mock_Client):
        Log.objects.all().delete()
        token = "token"
        device = Device.objects.create(token=token, os=Device.ANDROID_OS, arn="arn", user=User.objects.first())
        mock_response_1 = {"Enabled": "false", "Token": token}
        mock_Client().retrieve_platform_endpoint_attributs.return_value = mock_response_1
        mock_response_2 = {"EndpointArn": "arn"}
        mock_Client().create_android_platform_endpoint.return_value = mock_response_2
        mock_Client().delete_platform_endpoint.return_value = ""
        response = refresh_device(device)
        self.assertEqual(response, mock_response_1)
        self.assertEqual(device.arn, mock_response_2["EndpointArn"])

    @patch("polymarq_backend.apps.aws_sns.models.Client")
    def test_deregister(self, mock_Client):
        Log.objects.all().delete()
        token = "token"
        device = Device.objects.create(token=token, os=Device.ANDROID_OS, arn="arn", user=User.objects.first())
        mock_Client().delete_platform_endpoint.return_value = None
        response = deregister_device(device)
        self.assertEqual(response, mock_Client().delete_platform_endpoint.return_value)

    @patch("polymarq_backend.apps.aws_sns.models.Client")
    def test_publish_to_android(self, mock_Client):
        Log.objects.all().delete()
        token = "token"
        device = Device.objects.create(token=token, os=Device.ANDROID_OS, arn="arn", user=User.objects.first())

        mock_response = (
            "message",
            {
                "EndpointArn": "arn",
                "ResponseMetadata": {
                    "RetryAttempts": 0,
                    "HTTPHeaders": {
                        "x-amzn-requestid": "e08722bb-4218-5b6a-8e55-71fa82e9ffc3",
                        "content-length": "424",
                        "date": "Fri, 06 Apr 2018 18:38:40 GMT",
                        "content-type": "text/xml",
                    },
                    "HTTPStatusCode": 200,
                    "RequestId": "e08722bb-4218-5b6a-8e55-71fa82e9ffc3",
                },
            },
        )
        mock_Client().publish_to_android.return_value = mock_response
        response = send_sns_mobile_push_notification_to_device(
            device=device, notification_type="type", text="text", data={"a": "b"}, title="title"
        )
        self.assertEqual(response["ResponseMetadata"]["HTTPStatusCode"], 200)

        log = Log.objects.first()
        self.assertEqual(log.device_id, device.id)
        self.assertEqual(log.message, "message")
        self.assertEqual(log.response, json.dumps(mock_response[1]).replace('"', "'"))

    @patch("polymarq_backend.apps.aws_sns.models.Client")
    def test_publish_to_ios(self, mock_Client):
        Log.objects.all().delete()
        token = "token"
        device = Device.objects.create(token=token, os=Device.IOS_OS, arn="arn", user=User.objects.first())

        mock_response = (
            "message",
            {
                "EndpointArn": "arn",
                "ResponseMetadata": {
                    "RetryAttempts": 0,
                    "HTTPHeaders": {
                        "x-amzn-requestid": "e08722bb-4218-5b6a-8e55-71fa82e9ffc3",
                        "content-length": "424",
                        "date": "Fri, 06 Apr 2018 18:38:40 GMT",
                        "content-type": "text/xml",
                    },
                    "HTTPStatusCode": 200,
                    "RequestId": "e08722bb-4218-5b6a-8e55-71fa82e9ffc3",
                },
            },
        )
        mock_Client().publish_to_ios.return_value = mock_response

        response = send_sns_mobile_push_notification_to_device(
            device=device, notification_type="type", text="text", data={"a": "b"}, title="title"
        )
        self.assertEqual(response["ResponseMetadata"]["HTTPStatusCode"], 200)

        log = Log.objects.first()
        self.assertEqual(log.device_id, device.id)
        self.assertEqual(log.message, "message")
        self.assertEqual(log.response, json.dumps(mock_response[1]).replace('"', "'"))
