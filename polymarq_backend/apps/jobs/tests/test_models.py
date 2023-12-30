import base64

from django.core.files.base import ContentFile
from django.test import TestCase

from polymarq_backend.apps.jobs.models import Job
from polymarq_backend.apps.users.models import Client, Technician, User
from polymarq_backend.core.utils.base64_samples import image1


class JobModelTest(TestCase):
    # Set up non-modified objects used by all test methods
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
        client = Client.objects.create(user=user, account_type="individual")

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
        technician = Technician.objects.create(user=user)

        # Create Job
        Job.objects.create(
            technician=technician,
            client=client,
            name="Fix my Sink",
            description="My kitchen sink is leaking from under, I think it is \
                the pipes connecting to the tap and the drainage as well",
            location_address="17, lagos street. Nigeria",
            status="OPENED",
            min_price="2000",
            max_price="5000",
            location_longitude=0,
            location_latitude=0,
            duration=1,
            image=ContentFile(base64.urlsafe_b64decode(image1.split(";base64,")[1]), name="test_image"),
        )

    def test_location_address_label(self):
        job = Job.objects.filter().first()
        field_label = job._meta.get_field("location_address").verbose_name
        self.assertEqual(field_label, "location address")

    def test_location_longitude_label(self):
        job = Job.objects.filter().first()
        field_label = job._meta.get_field("location_longitude").verbose_name
        self.assertEqual(field_label, "location longitude")

    def test_location_latitude_label(self):
        job = Job.objects.filter().first()
        field_label = job._meta.get_field("location_latitude").verbose_name
        self.assertEqual(field_label, "location latitude")

    def test_name_max_length(self):
        job = Job.objects.filter().first()
        max_length = job._meta.get_field("name").max_length
        self.assertEqual(max_length, 150)

    def test_description_length(self):
        job = Job.objects.filter().first()
        max_length = job._meta.get_field("description").max_length
        self.assertEqual(max_length, 1000)

    def test_location_address_length(self):
        job = Job.objects.filter().first()
        max_length = job._meta.get_field("location_address").max_length
        self.assertEqual(max_length, 1000)

    def test_get_client_location_longitude(self):
        job = Job.objects.filter().first()
        self.assertEqual(job.client.user.longitude, 0)

    def test_get_client_location_latitude(self):
        job = Job.objects.filter().first()
        self.assertEqual(job.client.user.latitude, 0)
