from django.urls import include, path, reverse
from rest_framework import status
from rest_framework.test import APITestCase, URLPatternsTestCase

from config.urls import API_PATH_PREFIX
from polymarq_backend.apps.jobs.models import Job
from polymarq_backend.apps.users.models import Client, Technician, User


class JobTests(APITestCase, URLPatternsTestCase):
    @classmethod
    def setUpTestData(cls):
        # Create Client User
        user = User.user_manager.create_user(
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
        # Create Client
        Client.objects.create(user=user, account_type="individual")

        # Create Technician User
        user = User.user_manager.create_user(
            email="UserTechnician@gmail.com",
            password="polymarq",
            username="UserTechnician",
            first_name="Mattew",
            last_name="Grace",
            phone_number="+234805006070",
            longitude=0,
            latitude=0,
            is_technician=True,
            is_verified=True,
        )
        # Create Tecnician
        Technician.objects.create(user=user)

        cls.data = {
            "technician": Technician.objects.filter().first().id,
            "name": "Fix my Sink",
            "description": "My kitchen sink is leaking from under, I think it is"
            + " the pipes connecting to the tap and the drainage as well",
            "location_address": "17, lagos street. Nigeria",
            "status": "OPENED",
            "location_longitude": 0,
            "location_latitude": 0,
            "duration": 1,
            "image": "",
            "min_price": "2000",
            "max_price": "5000",
        }
        Job.objects.create(
            client=Client.objects.filter().first(),
            # Not passing Technician to test ListJobView
            # technician=Technician.objects.filter().first(),
            name="Fix my Sink",
            description="My kitchen sink is leaking from under, I think it is \
                the pipes connecting to the tap and the drainage as well",
            location_address="17, lagos street. Nigeria",
            status="OPENED",
            location_longitude=0,
            location_latitude=0,
            duration=1,
            min_price="2000",
            max_price="5000",
        )
        job_uuid = Job.objects.all().first().uuid
        cls.url = reverse("jobs:create-job")
        cls.url2 = reverse("jobs:list-jobs")
        cls.url3 = reverse("jobs:get-patch-delete-job", kwargs={"uuid": job_uuid})

        cls.IOS = 0
        cls.ANDROID = 1
        cls.device_token = "testToken"

    urlpatterns = [
        path(f"{API_PATH_PREFIX}job/", include("polymarq_backend.apps.jobs.urls", namespace="jobs_app")),
        path(f"{API_PATH_PREFIX}auth/", include("config.auth_api_router")),
    ]

    def test_create_job_with_authorized_user(self):
        # Login and get access token
        client_data = {
            "email": "UserClient@gmail.com",
            "password": "polymarq",
            "username": "UserClient",
            "device_type": self.ANDROID,
            "device_token": self.device_token,
        }
        response = self.client.post(reverse("auth-api:user-login"), client_data)
        access_token = response.data["result"]["tokens"]["access"]

        # Set authorization credentials
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        response = self.client.post(self.url, self.data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 3)  # check success response
        self.assertEqual(len(response.data["result"]), 16)  # check response data

    def test_create_job_with_image(self):
        # Login and get access token
        client_data = {
            "email": "UserClient@gmail.com",
            "password": "polymarq",
            "username": "UserClient",
            "device_type": self.ANDROID,
            "device_token": self.device_token,
        }
        response = self.client.post(reverse("auth-api:user-login"), client_data)
        access_token = response.data["result"]["tokens"]["access"]

        # Set authorization credentials
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        image = open("polymarq_backend/core/utils/test_image.png", "rb")
        self.data["image"] = image
        response = self.client.post(self.url, self.data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 3)  # check success response
        self.assertEqual(len(response.data["result"]), 16)  # check response data

    def test_create_job_with_unauthorized_user(self):
        response = self.client.post(self.url, self.data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(len(response.data), 2)  # check error response
        self.assertEqual(response.data["success"], False)  # check error response
        self.assertEqual(len(response.data["error"][0]), 3)  # check response data

    def test_create_job_with_forbidden_user(self):
        # Login and get access token
        technician_data = {
            "email": "UserTechnician@gmail.com",
            "password": "polymarq",
            "username": "UserTechnician",
            "device_type": self.ANDROID,
            "device_token": self.device_token,
        }
        response = self.client.post(reverse("auth-api:user-login"), technician_data)
        access_token = response.data["result"]["tokens"]["access"]

        # Set authorization credentials
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        response = self.client.post(self.url, self.data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(len(response.data), 2)  # check error response
        self.assertEqual(response.data["success"], False)  # check error response
        self.assertEqual(len(response.data["error"][0]), 3)  # check response data

    def test_get_job_list_with_authorized_user(self):
        # Login and get access token
        technician_data = {
            "email": "UserTechnican@gmail.com",
            "password": "polymarq",
            "username": "UserTechnician",
            "device_type": self.ANDROID,
            "device_token": self.device_token,
        }
        response = self.client.post(reverse("auth-api:user-login"), technician_data)
        access_token = response.data["result"]["tokens"]["access"]

        # Set authorization credentials
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        response = self.client.get(self.url2, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # check success response
        self.assertEqual(len(response.data["result"]), 2)  # check response data

    def test_get_job_list_with_query_params(self):
        # Login and get access token
        technician_data = {
            "email": "UserTechnican@gmail.com",
            "password": "polymarq",
            "username": "UserTechnician",
            "device_type": self.ANDROID,
            "device_token": self.device_token,
        }
        response = self.client.post(reverse("auth-api:user-login"), technician_data)
        access_token = response.data["result"]["tokens"]["access"]

        # Set authorization credentials
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        response = self.client.get(f"{self.url2}?name=test", format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # check success response
        self.assertEqual(len(response.data["result"]), 2)  # check response data
        self.assertEqual(len(response.data["result"]["data"]), 0)  # should be empty

    def test_job_list_with_unauthorized_user(self):
        response = self.client.get(self.url2, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(len(response.data), 2)  # check error response
        self.assertEqual(response.data["success"], False)  # check error response
        self.assertEqual(len(response.data["error"][0]), 3)  # check response data

    def test_get_job_with_authorized_user_technician(self):
        # Login and get access token
        technician_data = {
            "email": "UserTechnican@gmail.com",
            "password": "polymarq",
            "username": "UserTechnician",
            "device_type": self.ANDROID,
            "device_token": self.device_token,
        }
        response = self.client.post(reverse("auth-api:user-login"), technician_data)
        access_token = response.data["result"]["tokens"]["access"]

        # Set authorization credentials
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        response = self.client.get(self.url3, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # check success response
        self.assertEqual(len(response.data["result"]), 16)  # check response data

    def test_get_job_with_authorized_user_client(self):
        # Login and get access token
        client_data = {
            "email": "UserClient@gmail.com",
            "password": "polymarq",
            "username": "UserClient",
            "device_type": self.ANDROID,
            "device_token": self.device_token,
        }
        response = self.client.post(reverse("auth-api:user-login"), client_data)
        access_token = response.data["result"]["tokens"]["access"]

        # Set authorization credentials
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        response = self.client.get(self.url3, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # check success response
        self.assertEqual(len(response.data["result"]), 16)  # check response data

    def test_job_with_unauthorized_user(self):
        response = self.client.get(self.url3, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(len(response.data), 2)  # check error response
        self.assertEqual(response.data["success"], False)  # check error response
        self.assertEqual(len(response.data["error"][0]), 3)  # check response data

    def test_update_job_with_authorized_user(self):
        # Login and get access token
        client_data = {
            "email": "UserClient@gmail.com",
            "password": "polymarq",
            "username": "UserClient",
            "device_type": self.ANDROID,
            "device_token": self.device_token,
        }
        response = self.client.post(reverse("auth-api:user-login"), client_data)
        access_token = response.data["result"]["tokens"]["access"]

        # Set authorization credentials
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        response = self.client.patch(self.url3, {"name": "Change my door"}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(len(response.data), 3)  # check success response
        self.assertEqual(len(response.data["result"]), 16)  # check response data
        self.assertEqual(response.data["result"]["name"], "Change my door")  # check update

    def test_update_job_with_forbidden_user(self):
        # Login and get access token
        technician_data = {
            "email": "UserTechnician@gmail.com",
            "password": "polymarq",
            "username": "UserTechnician",
            "device_type": self.ANDROID,
            "device_token": self.device_token,
        }
        response = self.client.post(reverse("auth-api:user-login"), technician_data)
        access_token = response.data["result"]["tokens"]["access"]

        # Set authorization credentials
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        response = self.client.patch(self.url3, {"name": "Change my door"}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(len(response.data), 2)  # check error response
        self.assertEqual(response.data["success"], False)  # check error response
        self.assertEqual(len(response.data["error"][0]), 3)  # check response data

    def test_update_job_with_unauthorized_user(self):
        response = self.client.patch(self.url3, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(len(response.data), 2)  # check error response
        self.assertEqual(response.data["success"], False)  # check error response
        self.assertEqual(len(response.data["error"][0]), 3)  # check response data

    def test_delete_job_with_authorized_user(self):
        # Login and get access token
        client_data = {
            "email": "UserClient@gmail.com",
            "password": "polymarq",
            "username": "UserClient",
            "device_type": self.ANDROID,
            "device_token": self.device_token,
        }
        response = self.client.post(reverse("auth-api:user-login"), client_data)
        access_token = response.data["result"]["tokens"]["access"]

        # Set authorization credentials
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        response = self.client.delete(self.url3, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(response.data), 3)  # check success response
        self.assertEqual(len(response.data["result"]), 0)  # check response data

    def test_delete_job_with_forbidden_user(self):
        # Login and get access token
        technician_data = {
            "email": "UserTechnician@gmail.com",
            "password": "polymarq",
            "username": "UserTechnician",
            "device_type": self.ANDROID,
            "device_token": self.device_token,
        }
        response = self.client.post(reverse("auth-api:user-login"), technician_data)
        access_token = response.data["result"]["tokens"]["access"]

        # Set authorization credentials
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        response = self.client.delete(self.url3, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(len(response.data), 2)  # check error response
        self.assertEqual(response.data["success"], False)  # check error response
        self.assertEqual(len(response.data["error"][0]), 3)  # check response data

    def test_delete_job_with_unauthorized_user(self):
        response = self.client.delete(self.url3, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(len(response.data), 2)  # check error response
        self.assertEqual(response.data["success"], False)  # check error response
        self.assertEqual(len(response.data["error"][0]), 3)  # check response data
