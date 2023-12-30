# contains business logic for payments app
import random

from django.core.paginator import Page
from django.db.models import Sum
from django.db.models.query import QuerySet
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

# from polymarq_backend.apps.aws_sns.models import Device
# from polymarq_backend.apps.aws_sns.tasks import refresh_device
from polymarq_backend.apps.jobs.models import Job, Ping
from polymarq_backend.apps.notifications.models import Notification
from polymarq_backend.apps.notifications.utils import send_push_notifications
from polymarq_backend.apps.payments.models import JobIncrementalPayment, JobPriceQuotation, TechnicianBankAccount
from polymarq_backend.apps.payments.paystack.services import Paystack
from polymarq_backend.apps.payments.utils import uniform_float_sample
from polymarq_backend.apps.users.models import Technician

# from polymarq_backend.core.sender import Sender


class JobState:
    """
    An object for every job's transactional state

    Args:
        ping: The Ping that got accepted for the job

    Example:
        >>> job = Job()
        >>> JobState(job)
    """

    def __init__(self, job: Job) -> None:
        self.ping = job.pings.filter(status=Ping.ACCEPTED).first()  # type: ignore
        self.job = job
        self.errors = {}

    @property
    def transaction_cost(self) -> float:
        """
        Get Job Transaction cost
        """
        if self.ping.transaction_cost.amount:
            return float(self.ping.transaction_cost.amount)

        cost = round(
            random.uniform(0.05, 0.07) * float(self.ping.price_quote.amount) + 0.05 * self.job.duration,
            2,
        )
        self.ping.transaction_cost = cost
        self.ping.save()
        return cost

    @property
    def total_payable_amount(self):
        """
        Get the total amount a technician can receive
        """
        amount = float(self.ping.price_quote.amount) - self.transaction_cost  # type: ignore
        return round(amount, 2)

    @property
    def total_amount_paid(self):
        """
        Get the total balance remaining for a technician
        """
        total_paid_amount = self.job.incremental_payments.aggregate(Sum("amount"))["amount__sum"] or 0  # type: ignore
        return float(total_paid_amount)

    @property
    def total_balance_due(self):
        """
        Get the total balance remaining for a technician
        """
        balance = self.total_payable_amount - self.total_amount_paid
        return round(balance, 2)

    @property
    def completion_state(self):
        """
        Get Current Job Completion State
        """
        return float(self.job.completion_state)

    @property
    def latest_increment_payment(self):
        """
        Get latest incremental payment
        """
        queryset = self.job.incremental_payments  # type: ignore

        return queryset.latest("created_at") if queryset.count() else None


class JobPaymentService(JobState):
    """
    An object for all job state and
    incremental payment services and payment sequences for Polymarq
    """

    def get_completion_state(
        self,
        client_state: float,
        technician_state: float,
    ):
        """
        Calculates completion state base on both suggested state by client and technician

        Args:
            client_state (float): client job state
            technician_state (float): technician job state

        Returns:
            float: completion state
        """
        delta_client_state = client_state - self.completion_state  # ∆Sc
        delta_technician_state = technician_state - self.completion_state  # ∆Sv

        completion_value = (delta_client_state + delta_technician_state) / 2

        completion_percent = completion_value / 10

        return completion_percent

    def get_amount_by_completion_state(self, completion_state: float) -> float:
        """
        Get payment due according to job completion state.

        Args:
            completion_state (float): evaluated completion state

        Returns:
            float: amount payable for a completion state attained
        """
        completed = self.completion_state + completion_state * 10 > 9.75

        pay_amount = (
            self.total_balance_due if completed else self.total_balance_due * completion_state
        )  # disbursing total maount due on exceeding a completion state of 9.75

        if not completed and not completion_state > 0.175:
            self.errors = {
                "error": {
                    "code": "failed",
                    "message": "Payment Error",
                    "details": "Not a significant state progress.",
                }
            }
            raise ValueError("Not a significant state progress.")

        return round(pay_amount, 2)

    def validate_completion_state(self, state: float, raise_exception=False) -> bool:
        """
        Validates both the client and technician's completion state
        """
        valid = True
        if self.job.completion_state >= state:
            self.errors = {
                "error": {
                    "code": "failed",
                    "message": "Validation Error",
                    "details": "Job completion state not progressive.",
                }
            }
            valid = False

        if state > 10:
            self.errors = {
                "error": {
                    "code": "failed",
                    "message": "Validation Error",
                    "details": "Job completion state is out of bound (> 10).",
                }
            }
            valid = False

        if not valid and raise_exception:
            raise ValidationError(self.errors)

        return valid

    def initialize_payment(self):
        def wrapper(*args, **kwargs):
            increment, technician = self(*args, **kwargs)  # type: ignore
            if increment.client_state and increment.technician_state:
                args[0].make_incremental_payment(increment, technician)  # type: ignore

            return increment

        return wrapper

    @initialize_payment  # type: ignore
    # Initializes payment if both state has been unpdated from the client and technician
    def set_technician_state(self, state: float) -> tuple[JobIncrementalPayment, Technician]:
        """
        Set the suggested state from the technician
        """
        obj_list = self.job.incremental_payments.filter(technician_state=0.0)  # type: ignore
        if obj_list.exists():
            increment = obj_list.first()
            increment.technician_state = state
            increment.save()
            return increment, self.job.technician  # type: ignore

        increment = JobIncrementalPayment.objects.create(
            job=self.job,
            client=self.ping.client,
            technician=self.ping.technician,
            technician_state=state,
        )

        return increment, self.job.technician  # type: ignore

    @initialize_payment  # type: ignore
    # Initializes payment if both state has been unpdated from the client and technician
    def set_client_state(self, state: float) -> JobIncrementalPayment:
        """
        Set the suggested state from the client
        """

        obj_list = self.job.incremental_payments.filter(client_state=0.0)  # type: ignore
        if obj_list.count():
            increment = obj_list.first()
            increment.client_state = state
            increment.save()
            return increment

        increment = JobIncrementalPayment.objects.create(
            job=self.job,
            client=self.ping.client,
            technician=self.ping.technician,
            client_state=state,
        )

        return increment

    def notify_conflict(self) -> None:
        """
        Send a push notification to both technician and client on a job to resolve a state update
        """

        # Notify Client
        send_push_notifications(
            recipient=self.job.client.user,  # type: ignore
            notification_type=Notification.JOB,
            title="Job State Resolution",
            body="Your action is required to resolve a job progress state conflict."
            + "Kindly, Check your dashboard for more info.",
        )

        # Notify Technician
        send_push_notifications(
            recipient=self.job.technician.user,  # type: ignore
            notification_type=Notification.JOB,
            title="Job State Resolution",
            body="Your action is required to resolve a job progress state conflict."
            + "Kindly, Check your dashboard for more info.",
        )

    def validate_state_difference(self, client_state: float, technician_state: float) -> bool:
        difference = abs(client_state - technician_state)
        progress = abs(client_state + technician_state) - self.completion_state

        if difference > 4:
            self.notify_conflict()
            return False

        if progress < 1.75:
            return False

        return True

    def make_incremental_payment(
        self, increment: JobIncrementalPayment, technician: Technician
    ) -> JobIncrementalPayment:
        """
        Initiates an incremental payment for technician base on completion state
        """

        client_state = float(increment.client_state)
        technician_state = float(increment.technician_state)

        if not self.validate_state_difference(client_state, technician_state):
            return increment

        completion_state = self.get_completion_state(
            client_state=client_state,
            technician_state=technician_state,
        )

        amount = self.get_amount_by_completion_state(completion_state=completion_state)

        if amount <= 0:
            # self.errors = {
            #     "error": {
            #         "code": "failed",
            #         "message": "Payment Error",
            #         "details": "No unpaid balance left.",
            #     }
            # }
            raise ValueError("Out of balance due")

        # Update job completion state
        self.job.completion_state = float(self.job.completion_state) + completion_state * 10  # type: ignore

        if int(self.job.completion_state) == 10:
            self.job.status = self.job.VERIFIED

        self.job.save()

        # Initializing payment
        # Paystack logic for disbursing payment to technician should come here
        transaction_reference = None
        paystack = Paystack()

        try:
            technician_bank_info: TechnicianBankAccount = technician.technician_bank_account  # type: ignore
        except TechnicianBankAccount.DoesNotExist:
            raise serializers.ValidationError("Technician bank account not found")

        paystack.initiate_transfer(
            recipient_code=technician_bank_info.paystack_recipient_code,  # type: ignore
            amount=amount,
            reason=f"Polymarq payment for {self.job.name}",
        )

        # Updating the increment payment model
        increment.paid = True
        increment.amount = amount
        increment.transaction_reference = transaction_reference
        increment.save()

        return increment


class PaymentService:
    @staticmethod
    def retrieve_job_budget_range_based_on_ping_request_cycle(
        job: Job,
    ) -> tuple[float, float]:
        """
        Handles the logic for retrieving a price range for a job, based on the number of ping request cycle.

        Args:
            job (Job): Job object

        Returns:
            Tuple[float, float]: suggested min_price and max_price
        """
        if job.ping_request_cycle > 1:
            min_budget, max_budget = (
                job.min_price + ((job.min_price / 10) * job.ping_request_cycle),
                job.max_price,
            )
            # update job object on runtime and not save to db
            setattr(job, "min_price", min_budget)
            setattr(job, "max_price", max_budget)
            return min_budget.amount, max_budget.amount

        else:
            return job.min_price.amount, job.max_price.amount

    @staticmethod
    def calculate_price_quotations(job: Job, technicians: QuerySet | Page):  # type: ignore
        """
        Handles the logic for calculating price quotations for a job.

        Args:
            job (Job): Job object
            technicians (QuerySet | Page): QuerySet or Page object of technicians
        """

        (
            min_budget,
            max_budget,
        ) = PaymentService.retrieve_job_budget_range_based_on_ping_request_cycle(job)

        if isinstance(technicians, Page):
            num_of_sampled_technicians = technicians.object_list.count()
        else:
            num_of_sampled_technicians = technicians.count()

        if job.require_technicians_immediately:
            # override min_budget and max_budget
            (
                min_budget,
                max_budget,
            ) = PaymentService.calculate_budget_range_for_immediate_job(job)
            job_price_samples = uniform_float_sample(min_budget, max_budget, num_of_sampled_technicians)

        elif job.require_technicians_next_day:
            # override min_budget and max_budget
            (
                min_budget,
                max_budget,
            ) = PaymentService.calculate_budget_range_for_next_day_job(job)
            job_price_samples = uniform_float_sample(min_budget, max_budget, num_of_sampled_technicians)

        else:
            job_price_samples = uniform_float_sample(min_budget, max_budget, num_of_sampled_technicians)

        price_sample_and_technicians = zip(technicians, job_price_samples)

        job_price_quotations = [
            JobPriceQuotation(job=job, technician=technician, price=price)
            for technician, price in price_sample_and_technicians
        ]
        JobPriceQuotation.objects.bulk_create(job_price_quotations)
        job.increase_ping_request_cycle()

    @staticmethod
    def calculate_price_quotation(job: Job, technician: Technician):
        """
        Handles the logic for calculating price quotation for a job.

        Args:
            job (Job): Job object
            technician (Technician): Technician object

        Returns:
            float: price quotation
        """
        (
            min_budget,
            max_budget,
        ) = PaymentService.retrieve_job_budget_range_based_on_ping_request_cycle(job)

        if job.require_technicians_immediately:
            # override min_budget and max_budget
            (
                min_budget,
                max_budget,
            ) = PaymentService.calculate_budget_range_for_immediate_job(job)
            job_price_sample = uniform_float_sample(min_budget, max_budget, 1)[0]

        elif job.require_technicians_next_day:
            # override min_budget and max_budget
            (
                min_budget,
                max_budget,
            ) = PaymentService.calculate_budget_range_for_next_day_job(job)
            job_price_sample = uniform_float_sample(min_budget, max_budget, 1)[0]

        else:
            job_price_sample = uniform_float_sample(min_budget, max_budget, 1)[0]

        JobPriceQuotation.objects.create(job=job, technician=technician, price=job_price_sample)
        job.increase_ping_request_cycle()

        return job_price_sample

    @staticmethod
    def suggest_recommended_budget_range_from_technicians_responses(
        job: Job,
    ) -> tuple[float, float]:
        """
        Handles the logic for suggesting a recommended price for a job,
        when all pinged technicians decline a job request ping.

        Args:
            job (Job): Job object

        Returns:
            (float, float): recommended min_price and max_price
        """
        prices = Ping.objects.filter(job=job, status__in=[Ping.DECLINED, Ping.NEGOTIATING]).values_list(
            "price_quote", flat=True
        )

        median_price = float(sorted(prices)[len(prices) // 2])

        # generate two price samples between around the median price
        min_price = median_price - (0.1 * median_price)
        max_price = median_price + (0.1 * median_price)

        return min_price, max_price

    @staticmethod
    def calculate_budget_range_for_immediate_job(job: Job) -> tuple[float, float]:
        """
        Handles the logic surging price by suggesting a price range for an immediate job.

        Args:
            job (Job): Job object

        Returns:
            (float, float): suggested min_price and max_price
        """
        min_price = job.min_price
        max_price = job.max_price

        min_budget = (min_price + max_price) / 2
        max_budget = max_price

        return min_budget.amount, max_budget.amount

    @staticmethod
    def calculate_budget_range_for_next_day_job(job: Job) -> tuple[float, float]:
        """
        Handles the logic surging price by suggesting a price range for next day job.

        Args:
            job (Job): Job object

        Returns:
            (float, float): suggested min_price and max_price
        """
        min_price = job.min_price
        max_price = job.max_price

        min_budget = min_price + (min_price / 10)
        max_budget = max_price

        return min_budget.amount, max_budget.amount
