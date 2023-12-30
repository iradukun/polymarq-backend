from django.test import TestCase
from django.urls import reverse


class BaseTestCase(TestCase):
    username = None
    password = None
    ANDROID = None
    device_token = None

    def get_authorization_token(self):
        # Login and get access token
        client_data = {
            "username": self.username,
            "password": self.password,
            "device_type": self.ANDROID,
            "device_token": self.device_token,
        }
        url = reverse("auth-api:user-login")
        response = self.client.post(url, client_data, content_type="application/json").json()
        return response["result"]["tokens"]["access"]

    @property
    def headers(self):
        # Set authorization credentials
        token = self.get_authorization_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        return headers
