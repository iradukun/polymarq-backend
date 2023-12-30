from django.test import TestCase
from moneyed import Money

from polymarq_backend.apps.payments.models import JobPriceQuotation
from polymarq_backend.apps.payments.tests.factory import JobFactory, TechnicianFactory


class JobPriceQuotationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.job = JobFactory()
        cls.technician = TechnicianFactory()
        cls.job_price_quotation = JobPriceQuotation.objects.create(job=cls.job, technician=cls.technician, price=100.0)

    def test_job_price_quotation_creation(self):
        self.assertEqual(self.job_price_quotation.job, self.job)
        self.assertEqual(self.job_price_quotation.technician, self.technician)
        self.assertEqual(self.job_price_quotation.price, Money(100.0, "NGN"))
