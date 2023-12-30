from django.test import TestCase

from polymarq_backend.apps.tools.models import RentalRequest, Tool, ToolCategory
from polymarq_backend.apps.users.models import Technician, User


class TestToolCategoryModel(TestCase):
    name = "Cleaning"
    description = "Tools for cleaning service"

    def test_model_fields(self):
        tool = ToolCategory.objects.create(name=self.name, description=self.description)
        self.assertEqual(tool.name, self.name)
        self.assertEqual(tool.description, self.description)

    def test_optional_description(self):
        tool = ToolCategory.objects.create(name="Repair")
        self.assertIsInstance(tool.description, str)
        self.assertEqual(len(tool.description), 0)


class TestToolModel(TestCase):
    name = "Socket Wrench"
    description = "Tools for decoupling"
    price = 7000

    def test_model_fields(self):
        category = ToolCategory.objects.create(name="Wrenches")
        user = User.user_manager.create_user(
            email="techUser@example.com",
            password="polymarqTech",
            first_name="John",
            last_name="Doe",
            phone_number="+2348000000",
            longitude=0,
            latitude=0,
            is_technician=True,
            is_verified=True,
        )
        technician = Technician.objects.create(user=user)
        tool = Tool.objects.create(
            name=self.name, description=self.description, price=7000, owner=technician, category=category
        )
        self.assertEqual(tool.owner.uuid, technician.uuid)
        self.assertEqual(tool.name, self.name)
        self.assertEqual(tool.description, self.description)
        self.assertEqual(tool.price.amount, self.price)
        self.assertEqual(tool.category.name, category.name)


class TestRentalRequestModel(TestCase):
    name = "Socket Wrench"
    description = "Tools for decoupling"
    price = 7000

    def test_model_fields(self):
        category = ToolCategory.objects.create(name="Wrenches")
        user = User.user_manager.create_user(
            email="techUser@example.com",
            password="polymarqTech",
            first_name="John",
            last_name="Doe",
            phone_number="+2348000000",
            longitude=0,
            latitude=0,
            is_technician=True,
            is_verified=True,
        )
        technician = Technician.objects.create(user=user)
        tool = Tool.objects.create(
            name=self.name, description=self.description, price=7000, owner=technician, category=category
        )
        request = RentalRequest.objects.create(tool=tool, request_owner=technician, rental_duration=10, price=5000)

        self.assertEqual(request.tool.uuid, tool.uuid)
        self.assertEqual(str(request.request_owner.uuid), str(technician.uuid))
        self.assertEqual(request.price.amount, 5000)
        self.assertEqual(request.rental_duration, 10)
