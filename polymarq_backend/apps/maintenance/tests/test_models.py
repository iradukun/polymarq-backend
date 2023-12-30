import base64

from django.core.files.base import ContentFile
from django.test import TestCase

from polymarq_backend.apps.maintenance.models import Maintenance
from polymarq_backend.apps.users.models import Client, Technician, TechnicianType, User
from polymarq_backend.core.utils.base64_samples import image1


class MaintenanceModelTest(TestCase):
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

        # Create TechnicianType
        TechnicianType.objects.create(title="plumber")

        # Create Maintenance
        Maintenance.objects.create(
            client=client,
            technician=technician,
            frequency="WEEKLY",
            technician_type=TechnicianType.objects.get(title="plumber"),
            name="Home cleaning",
            description="someone (or people) to dust, sweep, mop etc the whole house \
                properly every week. it is a two bedroom apartment",
            image=ContentFile(base64.urlsafe_b64decode(image1.split(";base64,")[1]), name="test_image"),
            min_price="2000",
            max_price="5000",
            location_address="17, lagos street. Nigeria",
            location_longitude=0,
            location_latitude=0,
            duration=2,
        )

    def test_location_address_label(self):
        maintenance = Maintenance.objects.filter().first()
        field_label = maintenance._meta.get_field("location_address").verbose_name
        self.assertEqual(field_label, "location address")

    def test_location_longitude_label(self):
        maintenance = Maintenance.objects.filter().first()
        field_label = maintenance._meta.get_field("location_longitude").verbose_name
        self.assertEqual(field_label, "location longitude")

    def test_location_latitude_label(self):
        maintenance = Maintenance.objects.filter().first()
        field_label = maintenance._meta.get_field("location_latitude").verbose_name
        self.assertEqual(field_label, "location latitude")

    def test_name_max_length(self):
        maintenance = Maintenance.objects.filter().first()
        max_length = maintenance._meta.get_field("name").max_length
        self.assertEqual(max_length, 150)

    def test_description_length(self):
        maintenance = Maintenance.objects.filter().first()
        max_length = maintenance._meta.get_field("description").max_length
        self.assertEqual(max_length, 1000)

    def test_location_address_length(self):
        maintenance = Maintenance.objects.filter().first()
        max_length = maintenance._meta.get_field("location_address").max_length
        self.assertEqual(max_length, 1000)

    def test_frequency_default(self):
        maintenance = Maintenance.objects.filter().first()
        default = maintenance._meta.get_field("frequency").default
        self.assertEqual(default, "WEEKLY")

    def test_get_client_location_longitude(self):
        maintenance = Maintenance.objects.filter().first()
        self.assertEqual(maintenance.client.user.longitude, 0)

    def test_get_client_location_latitude(self):
        maintenance = Maintenance.objects.filter().first()
        self.assertEqual(maintenance.client.user.latitude, 0)
