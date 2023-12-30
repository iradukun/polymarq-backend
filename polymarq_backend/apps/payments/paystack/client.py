import requests
from django.conf import settings
from rest_framework.exceptions import ValidationError

from polymarq_backend.apps.payments.paystack.utils import validate_paystack_response


class PaystackClient:
    """
    A defined client for paystack services
    """

    def __init__(self) -> None:
        self.secret_key = settings.PAYSTACK_SECRET_KEY

        if not getattr(self, "secret_key", None):
            raise ValidationError("Set the `PAYSTACK_SECRET_KEY` variable")

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer { self.secret_key }",  # type: ignore
        }

    @validate_paystack_response
    def get(self, url: str, params: str | None = None, *args, **kwargs):  # type: ignore
        return requests.get(url=url, params=params, *args, **kwargs, headers=self.headers)

    @validate_paystack_response
    def post(self, url: str, data, params: str | None = None, *args, **kwargs):  # type: ignore
        return requests.post(url=url, json=data, params=params, headers=self.headers)

    @validate_paystack_response
    def put(self, url: str, data, params: str | None = None, *args, **kwargs):  # type: ignore
        return requests.put(url=url, json=data, params=params, headers=self.headers)

    @validate_paystack_response
    def patch(self, url: str, data, params: str | None = None, *args, **kwargs):  # type: ignore
        return requests.patch(url=url, json=data, params=params, headers=self.headers)

    @validate_paystack_response
    def delete(self, url: str, data, params: str | None = None, *args, **kwargs):  # type: ignore
        return requests.delete(url=url, json=data, params=params, headers=self.headers)
