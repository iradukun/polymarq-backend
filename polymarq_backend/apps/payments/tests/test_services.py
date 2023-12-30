from typing import cast

from django.test import TestCase

from polymarq_backend.apps.jobs.models import Job, Ping
from polymarq_backend.apps.payments.models import JobIncrementalPayment, JobPriceQuotation
from polymarq_backend.apps.payments.services import JobPaymentService, PaymentService
from polymarq_backend.apps.payments.tests.factory import JobFactory, TechnicianFactory
from polymarq_backend.apps.users.models import Technician


class PaymentServiceTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.job = cast(Job, JobFactory())

    def test_retrieve_job_budget_range_based_on_ping_request_cycle(self):
        (
            min_price,
            max_price,
        ) = PaymentService.retrieve_job_budget_range_based_on_ping_request_cycle(self.job)

        self.assertEqual(min_price, 100.0)
        self.assertEqual(max_price, 200.0)

        self.job.ping_request_cycle = 2
        (
            min_price,
            max_price,
        ) = PaymentService.retrieve_job_budget_range_based_on_ping_request_cycle(self.job)
        self.assertEqual(min_price, 120.0)
        self.assertEqual(max_price, 200.0)

    def test_calculate_price_quotations(self):
        technicians_list = TechnicianFactory.create_batch(2)
        technicians = Technician.objects.filter(id__in=[tech.id for tech in technicians_list])

        PaymentService.calculate_price_quotations(self.job, technicians)

        job_price_quotations = JobPriceQuotation.objects.all()
        self.assertEqual(len(job_price_quotations), 2)


class JobPaymentServiceTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.job = cast(Job, JobFactory())
        print(cls.job)
        cls.ping = Ping.objects.create(
            technician=cls.job.technician,
            client=cls.job.client,
            job=cls.job,
            distance_from_client=200,
            price_quote=5000.0,
            status=Ping.ACCEPTED,
        )

    def test_total_payable_amount(self):
        service = JobPaymentService(self.job)
        self.assertEqual(
            service.total_payable_amount,
            float(service.ping.price_quote.amount) - service.transaction_cost,
        )

    def test_get_completion_state(self):
        service = JobPaymentService(self.job)
        completion_state = service.get_completion_state(4, 6)
        self.assertEqual(completion_state, 0.5)

    def test_get_amount_by_completion_state(self):
        service = JobPaymentService(self.job)
        completion_state = service.get_completion_state(4, 6)
        amount = service.get_amount_by_completion_state(completion_state)
        self.assertEqual(amount, round(service.total_balance_due * completion_state, 2))

    def test_set_technician_state(self):
        service = JobPaymentService(self.job)
        service.set_technician_state(4)
        self.assertEqual(service.job.incremental_payments.latest("created_at").technician_state, 4)  # type: ignore

    def test_set_client_state(self):
        service = JobPaymentService(self.job)
        service.set_client_state(3)
        self.assertEqual(service.job.incremental_payments.latest("created_at").client_state, 3)  # type: ignore

    def test_make_incremental_payment(self):
        service = JobPaymentService(self.job)
        increment = JobIncrementalPayment.objects.create(
            job=self.job,
            client=self.job.client,
            technician=self.job.technician,
            client_state=3,
            technician_state=5,
        )
        service.make_incremental_payment(increment)

        self.assertTrue(increment.paid)
        self.assertEqual(float(increment.amount.amount), service.total_amount_paid)
