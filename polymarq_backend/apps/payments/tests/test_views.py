from django.urls import reverse

from polymarq_backend.apps.jobs.models import Job, Ping
from polymarq_backend.apps.payments.services import JobPaymentService
from polymarq_backend.apps.payments.tests.factory import BaseTestCase
from polymarq_backend.apps.users.models import Client, Technician, TechnicianType, User


class TestJobStateUpdate(BaseTestCase):
    email = "userTechnician@example.com"
    username = "userTechnician"
    password = "polymarqTechnician"
    IOS = 0
    ANDROID = 1
    device_token = "testToken"

    @classmethod
    def setUpTestData(cls):
        cls.user = User.user_manager.create_user(
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
            is_client=True,
            is_active=True,
        )
        cls.test_type = TechnicianType.objects.create(title="Automobile Engineer")

        cls.technician_data = {
            "professional_summary": "I'm a professional Engineer with 6+ Years of experience",
            "country": "Nigeria",
            "city": "Lagos",
            "local_government_area": "Alimosho",
            "work_address": "Ikotun",
            "services": "Home Maintenance",
            "years_of_experience": 9,
        }

        cls.technician = Technician.objects.create(user=cls.user, **cls.technician_data, job_title=cls.test_type)

        cls.client_user = Client.objects.create(user=cls.user, account_type="individual")

        cls.job = Job.objects.create(
            client=cls.client_user,
            technician=cls.technician,
            name="Fix my Sink",
            description="My kitchen sink is leaking from under, I think it is \
                the pipes connecting to the tap and the drainage as well",
            location_address="17, lagos street. Nigeria",
            status="OPENED",
            location_longitude=0,
            location_latitude=0,
            duration=1,
            min_price=2000,
            max_price=5000,
        )

        cls.ping = Ping.objects.create(
            technician=cls.technician,
            client=cls.client_user,
            job=cls.job,
            distance_from_client=200,
            price_quote=5000.0,
            status=Ping.ACCEPTED,
        )

    def test_technician_job_state_update(self):
        job = Job.objects.create(
            client=self.client_user,
            technician=self.technician,
            name="Fix my Sink",
            description="My kitchen sink is leaking from under, I think it is \
                the pipes connecting to the tap and the drainage as well",
            location_address="17, lagos street. Nigeria",
            status="OPENED",
            location_longitude=0,
            location_latitude=0,
            duration=1,
            min_price=2000,
            max_price=5000,
        )
        Ping.objects.create(
            technician=self.technician,
            client=self.client_user,
            job=job,
            distance_from_client=200,
            price_quote=5000.0,
            status=Ping.ACCEPTED,
        )

        url = reverse("payments:update-technician-job-state", args=[job.uuid])
        response = self.client.post(
            url, {"job_state": 2.0}, headers=self.headers, content_type="application/json"  # type: ignore
        )
        response_json = response.json()
        valid = lambda: float(job.incremental_payments.latest("created_at").technician_state) == 2.0  # type: ignore # noqa: E731, E501

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response_json["message"], "State updated succesfully.")
        self.assertTrue(valid())

    def test_client_job_state_update(self):
        job = Job.objects.create(
            client=self.client_user,
            technician=self.technician,
            name="Fix my Sink",
            description="My kitchen sink is leaking from under, I think it is \
                the pipes connecting to the tap and the drainage as well",
            location_address="17, lagos street. Nigeria",
            status="OPENED",
            location_longitude=0,
            location_latitude=0,
            duration=1,
            min_price=2000,
            max_price=5000,
        )
        Ping.objects.create(
            technician=self.technician,
            client=self.client_user,
            job=job,
            distance_from_client=200,
            price_quote=5000.0,
            status=Ping.ACCEPTED,
        )
        url = reverse("payments:update-client-job-state", args=[job.uuid])
        response = self.client.post(
            url, {"job_state": 3.0}, headers=self.headers, content_type="application/json"  # type: ignore
        )
        response_json = response.json()
        valid = lambda: float(job.incremental_payments.latest("created_at").client_state) == 3.0  # type: ignore # noqa: E731, E501

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response_json["message"], "State updated succesfully.")
        self.assertTrue(valid())

    def test_incremental_payments_list(self):
        job = Job.objects.create(
            client=self.client_user,
            technician=self.technician,
            name="Fix my Sink",
            description="My kitchen sink is leaking from under, I think it is \
                the pipes connecting to the tap and the drainage as well",
            location_address="17, lagos street. Nigeria",
            status="OPENED",
            location_longitude=0,
            location_latitude=0,
            duration=1,
            min_price=2000,
            max_price=5000,
        )
        Ping.objects.create(
            technician=self.technician,
            client=self.client_user,
            job=job,
            distance_from_client=200,
            price_quote=5000.0,
            status=Ping.ACCEPTED,
        )
        url = reverse("payments:incremental-payments-list", args=[job.uuid])
        response = self.client.get(url, headers=self.headers)  # type: ignore
        response_json = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response_json["result"]["data"], list)

    def test_intial_incremental_payment(self):
        job = Job.objects.create(
            client=self.client_user,
            technician=self.technician,
            name="Fix my Sink",
            description="My kitchen sink is leaking from under, I think it is \
                the pipes connecting to the tap and the drainage as well",
            location_address="17, lagos street. Nigeria",
            status="OPENED",
            location_longitude=0,
            location_latitude=0,
            duration=2,
            min_price=6000,
            max_price=8000,
        )
        Ping.objects.create(
            technician=self.technician,
            client=self.client_user,
            job=job,
            distance_from_client=200,
            price_quote=5000.0,
            status=Ping.ACCEPTED,
        )
        client_url = reverse("payments:update-client-job-state", args=[job.uuid])
        technician_url = reverse("payments:update-technician-job-state", args=[job.uuid])

        # Update Client Suggested Job state
        self.client.post(
            client_url, {"job_state": 4.0}, headers=self.headers, content_type="application/json"  # type: ignore
        )
        # Update Technician Suggested Job state
        self.client.post(
            technician_url, {"job_state": 6.0}, headers=self.headers, content_type="application/json"  # type: ignore
        )
        job = Job.objects.get(pk=job.pk)  # type: ignore
        job_manager = JobPaymentService(job)

        self.assertEqual(job_manager.completion_state, 5.0)
        self.assertEqual(
            job_manager.total_amount_paid,
            float(job.incremental_payments.first().amount.amount),  # type: ignore
        )
