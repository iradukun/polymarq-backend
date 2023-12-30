import uuid
from uuid import UUID

from django.conf import settings

from polymarq_backend.apps.payments.paystack.client import PaystackClient
from polymarq_backend.apps.payments.paystack.constants import ItemType
from polymarq_backend.apps.users.types import UserType


class PaystackBase:
    BASE_URL = "https://api.paystack.co"
    BANKS_URL = BASE_URL + "/bank"
    TRANSFER_RECIPIENT_URL = BASE_URL + "/transferrecipient"
    SUBACCOUNT_URL = BASE_URL + "/subaccount"
    TRANSFER_URL = BASE_URL + "/transfer"
    INITIALIZE_TRANSACTION_URL = BASE_URL + "/transaction/initialize"

    @property
    def client(self):
        return PaystackClient()


class Paystack(PaystackBase):
    # def __init__(self, secret_key: str | None = None) -> None:  # type: ignore
    #     self.secret_key = secret_key if secret_key else self.secret_key

    def create_transfer_recipient(
        self,
        name: str,
        bank_code: str,
        account_number: str,
        recipient_type: str = "nuban",
        currency: str = "NGN",
    ):
        data = {
            "type": recipient_type,
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": currency,
        }
        response_data = self.client.post(self.TRANSFER_RECIPIENT_URL, data=data)
        return response_data

    def create_subaccount(
        self,
        customer_name: str,
        bank_code: str,
        account_number: str,
        percentage_charge: float = float(settings.PAYSTACK_SUBACCOUNT_PERCENTAGE_FEE),
    ):
        data = {
            "business_name": customer_name,
            "account_number": account_number,
            "bank_code": bank_code,
            "percentage_charge": percentage_charge,
        }
        response_data = self.client.post(self.SUBACCOUNT_URL, data=data)
        return response_data

    def initiate_transfer(self, recipient_code: str, amount: float, *, reason: str = "Polymarq payout"):
        if isinstance(amount, int):
            rounded_amount = amount
        elif isinstance(amount, float):
            rounded_amount = round(amount, 2)
        else:
            raise ValueError("Invalid amount type. Amount must be an int or float.")

        data = {
            "source": "balance",
            "amount": rounded_amount * 100,  # amount in kobo
            "recipient": recipient_code,
            "reason": reason,
        }
        response_data = self.client.post(self.TRANSFER_URL, data=data)
        return response_data

    def finalize_transfer(self, transfer_id: str, otp: str):
        data = {
            "transfer_code": transfer_id,
            "otp": otp,
        }
        response_data = self.client.post(self.TRANSFER_URL, data=data)
        return response_data

    def initiate_subaccount_transaction(
        self,
        user: UserType,
        amount: int | float,
        subaccount_code: str,
        reference: str | UUID | None = None,
        *,
        item_type=ItemType.TOOL,
    ):
        if isinstance(amount, int):
            rounded_amount = amount
        elif isinstance(amount, float):
            rounded_amount = round(amount, 2)
        else:
            raise ValueError("Invalid amount type. Amount must be an int or float.")

        data = {
            "email": user.email,
            "amount": rounded_amount * 100,  # amount in kobo
            "reference": f"{item_type.value}-{reference}"
            if reference
            else f"{item_type.value}-{uuid.uuid4()}",  # generate a unique reference
            "subaccount": subaccount_code,  # subaccount code
        }

        response = self.client.post(self.INITIALIZE_TRANSACTION_URL, data=data)
        # response.raise_for_status()
        return response
