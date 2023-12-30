from django.urls import reverse

from polymarq_backend.apps.tools.models import RentalRequest, Tool, ToolCategory
from polymarq_backend.apps.tools.tests.factory import BaseTestCase
from polymarq_backend.apps.users.models import Technician, TechnicianType, User


class TestToolCategoryView(BaseTestCase):
    email = "userCategory@example.com"
    username = "userCategory"
    name = "Cleaning Tools"
    description = "Tools for cleaning services"
    password = "polymarqCategory33"
    IOS = 0
    ANDROID = 1
    device_token = "testToken"

    @classmethod
    def setUpTestData(cls):
        User.user_manager.create_user(
            email=cls.email,
            username=cls.username,
            password=cls.password,
            first_name="John",
            last_name="Doe",
            phone_number="+234800000000",
            longitude=0,
            latitude=0,
            is_verified=True,
            is_technician=True,
            is_active=True,
        )
        cls.tool = ToolCategory.objects.create(name=cls.name, description=cls.description)

    # def test_create_category(self):
    #     url = reverse("tools:tool-categories")
    #     name = "Washing Tools"
    #     description = "Tools for washing services"
    #     response = self.client.post(
    #         url,
    #         dict(name=name, description=description),
    #         headers=self.headers,  # type: ignore
    #         content_type="application/json",
    #     )
    #     response_json = response.json()

    #     self.assertEqual(response.status_code, 201)
    #     self.assertEqual(response_json["message"], "Resource created successfully.")
    #     self.assertEqual(response_json["result"]["name"], name)
    #     self.assertEqual(response_json["result"]["description"], description)

    def test_get_categories_list(self):
        url = reverse("tools:tool-categories")
        response = self.client.get(
            url + "?limit=all",
            headers=self.headers,  # type: ignore
        )
        response_json = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json["message"], "Resource fetched successfully.")
        self.assertEqual(response_json["result"]["count"], len(response_json["result"]["data"]))
        self.assertIsInstance(response_json["result"]["data"], list)

    def test_categories_search_query(self):
        ToolCategory.objects.create(name="Test Category")

        url = reverse("tools:tool-categories")
        query = "cleaning"
        response = self.client.get(
            f"{url}?q={query}",
            headers=self.headers,  # type: ignore
        )
        response_json = response.json()
        validate = lambda result: not bool(  # noqa E731
            [
                x
                for x in result
                if query.lower() not in x["name"].lower() and query.lower() not in x["description"].lower()
            ]
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json["message"], "Resource fetched successfully.")
        self.assertTrue(validate(response_json["result"]["data"]))

    def test_categories_asc_sort_order(self):
        ToolCategory.objects.create(name="Test Category 1")
        url = reverse("tools:tool-categories")
        response = self.client.get(
            f"{url}?order=asc",
            headers=self.headers,  # type: ignore
        )
        response_json = response.json()
        validate = lambda result: result == sorted(result, key=lambda x: x["name"])  # noqa E731  # noqa E731

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json["message"], "Resource fetched successfully.")
        self.assertTrue(validate(response_json["result"]["data"]))

    def test_categories_desc_sort_order(self):
        ToolCategory.objects.create(name="Test Category 2")

        url = reverse("tools:tool-categories")
        response = self.client.get(
            f"{url}?order=desc",
            headers=self.headers,  # type: ignore
        )
        response_json = response.json()
        validate = lambda result: result == sorted(result, key=lambda x: x["name"], reverse=True)  # noqa E731

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json["message"], "Resource fetched successfully.")
        self.assertTrue(validate(response_json["result"]["data"]))

    def test_categories_page_limit(self):
        # Creating more categories to test the limit properly
        ToolCategory.objects.create(name="Test Category 3")
        ToolCategory.objects.create(name="Test Category 4")

        url = reverse("tools:tool-categories")
        limit = 2
        response = self.client.get(
            f"{url}?limit={limit}",
            headers=self.headers,  # type: ignore
        )
        response_json = response.json()
        validate = lambda result: len(result) == limit  # noqa E731

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json["message"], "Resource fetched successfully.")
        self.assertTrue(validate(response_json["result"]["data"]))


class TestToolView(BaseTestCase):
    technician_type_title = "Automobile Engineer"
    professional_summary = "I'm a professional Engineer with 6+ Years of experience"
    address = "123, Lagos Island"
    email = "userTool@example.com"
    username = "userTool"
    name = "Strap Wrenches"
    description = "Tools for decoupling"
    password = "polymarqTool"
    IOS = 0
    ANDROID = 1
    device_token = "testToken"

    @classmethod
    def setUpTestData(cls):
        cls.test_type = TechnicianType.objects.create(title="Automobile Engineer")
        cls.technician_data = {
            "professional_summary": cls.professional_summary,
            "country": "Nigeria",
            "city": "Lagos",
            "local_government_area": "Alimosho",
            "work_address": "Ikotun",
            "services": "Home Maintenance",
            "years_of_experience": 9,
        }
        cls.user = cls.create_technician_user(cls, cls.email)  # type: ignore
        cls.tool_category = ToolCategory.objects.create(
            name="Wrenches",
        )
        cls.tool = Tool.objects.create(
            name=cls.name,
            category=cls.tool_category,
            price=20000,
            owner=cls.user,
            negotiable=True,
        )

    def create_technician_user(self, email):
        user = User.user_manager.create_user(
            email=email,
            username=self.username,
            password=self.password,
            first_name="John",
            last_name="Doe",
            phone_number="+234800000000",
            longitude=0,
            latitude=0,
            is_verified=True,
            is_technician=True,
            is_active=True,
        )
        technician_data = self.technician_data.copy()
        return Technician.objects.create(user=user, **technician_data, job_title=self.test_type)

    def create_tool(self, name, price=10000, negotiable=True, description=None):
        return Tool.objects.create(
            name=name,
            category=self.tool_category,
            description=description,
            price=price,
            owner=self.user,
            negotiable=negotiable,
        )

    def test_create_tool(self):
        url = reverse("tools:create-tools")
        data = {
            "name": "Strap Wrenches B",
            "price": "6000",
            "category": "Wrench",
            "negotiable": True,
            "is_available": True,
        }
        headers = self.headers.copy()
        del headers["Content-Type"]

        response = self.client.post(
            url,
            data=data,
            headers=headers,  # type: ignore
            format="multipart",
        )
        response_json = response.json()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response_json["result"]["name"], data["name"])
        self.assertEqual(response_json["result"]["negotiable"], data["negotiable"])
        self.assertEqual(response_json["result"]["isAvailable"], data["is_available"])
        self.assertEqual(response_json["result"]["category"]["name"], "Others")

    def test_tools_search_query(self):
        url = reverse("tools:list-tools")
        query = "strap"
        response = self.client.get(url + f"?q={query}", headers=self.headers)  # type: ignore
        response_json = response.json()

        validate = lambda result: not bool(  # noqa E731
            [
                x
                for x in result
                if query not in x["name"].lower()
                and query not in x["description"].lower()
                and query not in x["category"]["name"].lower()
            ]
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response_json["result"]["count"], int)
        self.assertTrue(validate(response_json["result"]["data"]))

    def test_tools_search_asc_sort_order(self):
        url = reverse("tools:list-tools")
        response = self.client.get(url + "?order=asc", headers=self.headers)  # type: ignore
        response_json = response.json()

        validate = lambda result: result == sorted(result, key=lambda x: x["name"])  # noqa E731

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json["message"], "Resource fetched successfully.")
        self.assertTrue(validate(response_json["result"]["data"]))

    def test_tools_search_desc_sort_order(self):
        url = reverse("tools:list-tools")
        response = self.client.get(url + "?order=desc", headers=self.headers)  # type: ignore
        response_json = response.json()

        validate = lambda result: result == sorted(result, key=lambda x: x["name"], reverse=True)  # noqa E731

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json["message"], "Resource fetched successfully.")
        self.assertTrue(validate(response_json["result"]["data"]))

    def test_tools_search_page_limit(self):
        self.create_tool("Pipe wrench")
        url = reverse("tools:list-tools")
        limit = 2
        response = self.client.get(url + f"??limit={limit}", headers=self.headers)  # type: ignore
        response_json = response.json()
        validate = lambda result: len(result) <= limit  # noqa E731

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json["message"], "Resource fetched successfully.")
        self.assertTrue(validate(response_json["result"]["data"]))

    def test_get_single_tool(self):
        name, price = "Pipe Wrench B", 2500
        tool = self.create_tool(name, price=price)
        url = reverse("tools:tool-detail", args=[tool.uuid])
        response = self.client.get(url, headers=self.headers)  # type: ignore
        response_json = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json["result"]["uuid"], str(tool.uuid))
        self.assertEqual(response_json["result"]["name"], name)
        self.assertEqual(int(float(response_json["result"]["price"])), price)

    def test_update_single_tool(self):
        name, price = "Pipe Wrench B", 2500
        tool = self.create_tool(name, price=price, negotiable=True)
        url = reverse("tools:tool-detail", args=[tool.uuid])
        response = self.client.patch(
            url,
            data=dict(negotiable=False, is_available=False),
            content_type="application/json",
            headers=self.headers,  # type: ignore
        )
        response_json = response.json()

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response_json["result"]["uuid"], str(tool.uuid))
        self.assertEqual(response_json["result"]["name"], name)
        self.assertEqual(response_json["result"]["negotiable"], False)
        self.assertEqual(response_json["result"]["isAvailable"], False)

    def test_delete_single_tool(self):
        name, price = "Pipe Wrench B", 2500
        tool = self.create_tool(name, price=price, negotiable=True)
        url = reverse("tools:tool-detail", args=[tool.uuid])
        response = self.client.delete(url, headers=self.headers)  # type: ignore
        valid = lambda: Tool.objects.filter(uuid=tool.uuid, is_deleted=False).count() == 0  # noqa: E731
        self.assertEqual(response.status_code, 204)
        self.assertTrue(valid())


class ToolRentalRequest(BaseTestCase):
    technician_type_title = "Automobile Engineer"
    professional_summary = "I'm a professional Engineer with 6+ Years of experience"
    address = "123, Lagos Island"
    email = "userRenter@example.com"
    username = "userRenter"
    name = "Strap Wrenches"
    description = "Tools for decoupling"
    password = "polymarqRequest"
    IOS = 0
    ANDROID = 1
    device_token = "testToken"

    @classmethod
    def setUpTestData(cls):
        cls.test_type = TechnicianType.objects.create(title="Automobile Engineer")
        cls.technician_data = {
            "professional_summary": cls.professional_summary,
            "country": "Nigeria",
            "city": "Lagos",
            "local_government_area": "Alimosho",
            "work_address": "Ikotun",
            "services": "Home Maintenance",
            "years_of_experience": 9,
        }
        cls.user = cls.create_technician_user(cls, cls.email)  # type: ignore

        cls.tool_category = ToolCategory.objects.create(
            name="Wrenches",
        )
        cls.tool = Tool.objects.create(
            name=cls.name,
            category=cls.tool_category,
            price=20000,
            owner=cls.user,
            negotiable=True,
        )

    def create_technician_user(self, email):
        user = User.user_manager.create_user(
            email=email,
            username=self.username,
            password=self.password,
            first_name="John",
            last_name="Doe",
            phone_number="+234800000000",
            longitude=0,
            latitude=0,
            is_verified=True,
            is_technician=True,
            is_active=True,
        )
        technician_data = self.technician_data.copy()
        return Technician.objects.create(user=user, **technician_data, job_title=self.test_type)

    def create_tool(self, name, price=10000, negotiable=True, description=None):
        return Tool.objects.create(
            name=name,
            category=self.tool_category,
            description=description,
            price=price,
            owner=self.user,
            negotiable=negotiable,
        )

    def test_create_rent_request(self):
        url = reverse("tools:tool-rent-request")
        data = {"tool": str(self.tool.uuid), "rental_duration": 12, "price": 8000}
        response = self.client.post(
            url, data=data, headers=self.headers, content_type="application/json"  # type: ignore
        )
        response_json = response.json()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response_json["result"]["requestOwner"]["uuid"], str(self.user.uuid))
        self.assertEqual(response_json["result"]["rentalDuration"], 12)
        self.assertEqual(response_json["result"]["price"], "8000.00")

    def test_get_rent_request(self):
        request = RentalRequest.objects.create(
            tool=self.tool, request_owner=self.user, rental_duration=10, price=12000
        )

        url = reverse("tools:rent-request-detail", args=[request.uuid])
        response = self.client.get(url, headers=self.headers)  # type: ignore
        response_json = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json["result"]["uuid"], str(request.uuid))
        self.assertEqual(response_json["result"]["tool"], str(self.tool.uuid))

    def test_update_rent_request(self):
        request = RentalRequest.objects.create(
            tool=self.tool, request_owner=self.user, rental_duration=10, price=12000
        )

        url = reverse("tools:rent-request-detail", args=[request.uuid])
        response = self.client.patch(
            url,
            data={"request_status": "rejected"},
            headers=self.headers,  # type: ignore
            content_type="application/json",
        )
        response_json = response.json()

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response_json["result"]["uuid"], str(request.uuid))
        self.assertEqual(response_json["result"]["requestStatus"], "rejected")

    def test_delete_rent_request(self):
        request = RentalRequest.objects.create(
            tool=self.tool, request_owner=self.user, rental_duration=10, price=12000
        )

        url = reverse("tools:rent-request-detail", args=[request.uuid])
        response = self.client.delete(url, headers=self.headers)  # type: ignore
        valid = lambda: RentalRequest.objects.filter(uuid=request.uuid, is_deleted=False).count() == 0  # noqa: E731

        self.assertEqual(response.status_code, 204)
        self.assertTrue(valid())

    def test_accept_rental_request(self):
        request = RentalRequest.objects.create(
            tool=self.tool, request_owner=self.user, rental_duration=10, price=12000
        )
        url = reverse("tools:accept-rent-request", args=[request.uuid])
        response = self.client.put(url, headers=self.headers, content_type="application/json")  # type: ignore
        response_json = response.json()
        valid = (
            lambda: RentalRequest.objects.get(uuid=request.uuid).request_status == RentalRequest.RequestStatus.ACCEPTED
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response_json["message"], "Request Accepted succesfully.")
        self.assertTrue(valid())

    def test_decline_rental_request(self):
        request = RentalRequest.objects.create(
            tool=self.tool, request_owner=self.user, rental_duration=10, price=12000
        )
        url = reverse("tools:decline-rent-request", args=[request.uuid])
        response = self.client.put(url, headers=self.headers, content_type="application/json")  # type: ignore
        response_json = response.json()
        valid = (
            lambda: RentalRequest.objects.get(uuid=request.uuid).request_status == RentalRequest.RequestStatus.REJECTED
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response_json["message"], "Request Declined succesfully.")
        self.assertTrue(valid())
