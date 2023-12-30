import factory
from django.test import TestCase
from django.urls import reverse

from polymarq_backend.apps.jobs.models import Job, Ping
from polymarq_backend.apps.users.models import Client, Technician, User


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


class JobFactory(factory.django.DjangoModelFactory):  # type: ignore
    class Meta:
        model = Job

    # technician
    # id = random.randint(1, 100)
    name = factory.Faker("name")  # type: ignore
    description = factory.Faker("text")  # type: ignore
    status = Job.PENDING
    location_longitude = factory.Faker("longitude")  # type: ignore
    location_latitude = factory.Faker("latitude")  # type: ignore
    duration = 3
    min_price = 100.0
    max_price = 200.0
    require_technicians_immediately = False
    require_technicians_next_day = False
    ping_request_cycle = 1
    client = factory.SubFactory("polymarq_backend.apps.payments.tests.factory.ClientFactory")  # type: ignore
    technician = factory.SubFactory("polymarq_backend.apps.payments.tests.factory.TechnicianFactory")  # type: ignore


class PingFactory(factory.django.DjangoModelFactory):  # type: ignore
    class Meta:
        model = Ping

    technician = factory.SubFactory("polymarq_backend.apps.payments.tests.factory.TechnicianFactory")  # type: ignore
    client = factory.SubFactory("polymarq_backend.apps.payments.tests.factory.ClientFactory")  # type: ignore
    job = factory.SubFactory("polymarq_backend.apps.payments.tests.factory.JobFactory")  # type: ignore
    distance_from_client = 200.0
    price_quote = 5000.0
    status = Ping.ACCEPTED


class UserFactory(factory.django.DjangoModelFactory):  # type: ignore
    class Meta:
        model = User

    # id = random.randint(1, 100)
    email = factory.Faker("email")  # type: ignore
    password = factory.Faker("password")  # type: ignore
    first_name = factory.Faker("name")  # type: ignore
    last_name = factory.Faker("name")  # type: ignore
    username = factory.Faker("email")  # type: ignore
    phone_number = "08070000000"  # type: ignore
    longitude = factory.Faker("longitude")  # type: ignore
    latitude = factory.Faker("latitude")  # type: ignore
    is_technician = True
    is_verified = True


class TechnicianFactory(factory.django.DjangoModelFactory):  # type: ignore
    class Meta:
        model = Technician

    # id = random.randint(1, 100)
    user = factory.SubFactory(UserFactory)  # type: ignore
    professional_summary = factory.Faker("text")  # type: ignore


class ClientFactory(factory.django.DjangoModelFactory):  # type: ignore
    class Meta:
        model = Client

    # id = random.randint(1, 100)
    user = factory.SubFactory(UserFactory)  # type: ignore
