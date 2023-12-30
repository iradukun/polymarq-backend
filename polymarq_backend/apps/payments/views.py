import hashlib
import hmac

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.views import APIView

from polymarq_backend.apps.jobs.models import Job, Ping
from polymarq_backend.apps.notifications.models import Notification
from polymarq_backend.apps.notifications.utils import send_push_notifications
from polymarq_backend.apps.payments.models import Bank, JobInitialPayment, TechnicianBankAccount, ToolPurchase
from polymarq_backend.apps.payments.paystack.constants import ItemType
from polymarq_backend.apps.payments.paystack.services import Paystack
from polymarq_backend.apps.payments.serializers import (
    BankSerializer,
    JobIncrementalPaymentCountSerializer,
    JobIncrementalPaymentSerializer,
    JobStateSerializer,
    TechnicianBankAccountCreateSerializer,
)
from polymarq_backend.apps.payments.services import JobPaymentService
from polymarq_backend.apps.tools.utils import FILTER_PARAMS
from polymarq_backend.apps.users.api.serializers import ErrorResponseSerializer
from polymarq_backend.core.decorators import client_required, technician_required
from polymarq_backend.core.error_response import ErrorResponse
from polymarq_backend.core.success_response import SuccessResponse, SuccessResponseSerializer
from polymarq_backend.core.utils.main import add_count


class TechnicianJobStateView(APIView):
    @extend_schema(
        request=JobStateSerializer,
        responses={
            201: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Status updated succesfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Payments"],
        description="Update Technician job state",
    )
    @technician_required
    def post(self, request, job_uuid):
        if not request.data.get("job_state"):
            return ErrorResponse(status=status.HTTP_403_FORBIDDEN, message="No job state in the payload.")

        state = float(request.data["job_state"])
        job = get_object_or_404(Job, uuid=job_uuid, pings__status=Ping.ACCEPTED)
        job_manager = JobPaymentService(job=job)

        job_manager.validate_completion_state(state, raise_exception=True)
        job_manager.set_technician_state(float(request.data["job_state"]))

        return SuccessResponse(status=status.HTTP_201_CREATED, message="State updated succesfully.")


class ClientJobStateView(APIView):
    @extend_schema(
        request=JobStateSerializer,
        responses={
            201: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Status updated succesfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Payments"],
        description="Update Client job state",
    )
    @client_required()  # type: ignore
    def post(self, request, job_uuid):
        if not request.data.get("job_state"):
            return ErrorResponse(status=status.HTTP_403_FORBIDDEN, message="No job state in the payload.")

        state = float(request.data["job_state"])
        job = get_object_or_404(Job, uuid=job_uuid, pings__status=Ping.ACCEPTED)
        job_manager = JobPaymentService(job=job)

        job_manager.validate_completion_state(state, raise_exception=True)
        job_manager.set_client_state(state)

        return SuccessResponse(status=status.HTTP_201_CREATED, message="State updated succesfully.")


class JobIncrementalPaymentListView(APIView):
    serializer_class = JobIncrementalPaymentSerializer

    @extend_schema(
        operation_id="job_incremental_payments_list",
        responses={
            200: OpenApiResponse(
                response=JobIncrementalPaymentCountSerializer,
                description="Resource fetched successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Payments"],
        description="Fetch all incremental payments for a job",
    )
    def get(self, request, job_uuid):
        job = get_object_or_404(Job, uuid=job_uuid, is_deleted=False)
        incremental_payments = job.incremental_payments.filter(paid=True)  # type: ignore
        serializer = self.serializer_class(incremental_payments, many=True)
        data = add_count(serializer.data, incremental_payments.count())
        return SuccessResponse(data=data, status=status.HTTP_200_OK)


class CreateTechnicianBankAccountInformationView(APIView):
    serializer_class = TechnicianBankAccountCreateSerializer

    @extend_schema(
        operation_id="technician_bank_account_create",
        request=TechnicianBankAccountCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Resource created successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Payments"],
        description="Create a bank account information for a technician",
    )
    @technician_required
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        bank_slug = data["bank_slug"]  # type: ignore
        bank = get_object_or_404(Bank, slug=bank_slug)

        technician = request.user.technician
        (
            technician_bank_account,
            _created,
        ) = TechnicianBankAccount.objects.update_or_create(
            technician=technician,
            defaults={
                "bank": bank,
                "account_name": data["account_name"],  # type: ignore
                "account_number": data["account_number"],  # type: ignore
            },
        )

        # create paystack recipient info
        paystack = Paystack()
        paystack_transfer_recipient_response = paystack.create_transfer_recipient(
            name=technician.user.full_name,
            bank_code=bank.code,
            account_number=data["account_number"],  # type: ignore
        )

        paystack_subaccount_response = paystack.create_subaccount(
            customer_name=technician.user.full_name,
            bank_code=bank.code,
            account_number=data["account_number"],  # type: ignore
        )

        if paystack_transfer_recipient_response["status"]:  # type: ignore
            technician_bank_account.paystack_recipient_code = paystack_transfer_recipient_response["data"]["recipient_code"]  # type: ignore # noqa: E501
            technician_bank_account.save(update_fields=["paystack_recipient_code"])

        if paystack_subaccount_response["status"]:  # type: ignore
            technician_bank_account.paystack_subaccount_code = paystack_subaccount_response["data"]["subaccount_code"]  # type: ignore # noqa: E501
            technician_bank_account.save(update_fields=["paystack_subaccount_code"])

        return SuccessResponse(
            status=status.HTTP_201_CREATED,
            message="Bank account information created successfully.",
        )


class PaystackTransactionsWebhook(APIView):
    EVENT_SUCCESS = "charge.success"

    @extend_schema(
        operation_id="paystack_transactions_webhook",
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Resource created successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Payments"],
        description="Paystack transactions webhook",
    )
    def post(self, request):
        request_body = request.body
        secret_key = settings.PAYSTACK_SECRET_KEY
        x_paystack_signature = request.headers.get("x-paystack-signature")
        try:
            # generate signature header from request data to verify the request is from paystack
            # Generate HMAC hash using SHA-512 and the secret key
            generated_hash = hmac.new(
                secret_key.encode("utf-8"),
                request_body,
                digestmod=hashlib.sha512,
            ).hexdigest()

            if generated_hash == x_paystack_signature:
                event_success = request.data.get("event")  # type: ignore
                transaction_status = request.data.get("data").get("status")  # type: ignore
                # payment_timestamp = request.data.get("data").get("paid_at")  # type: ignore
                # payment_date = datetime.strptime(
                #     payment_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ"
                # ).date()

                if event_success == self.EVENT_SUCCESS and transaction_status == "success":
                    # get the transaction ref
                    transaction_ref = request.data.get("data").get("reference")  # type: ignore
                    item_type = transaction_ref.split("-")[0]

                    if item_type == ItemType.TOOL.value:
                        # check tool purchase to complete payment
                        tool_purchase = get_object_or_404(ToolPurchase, transaction_reference=transaction_ref)

                        tool_purchase.paid = True
                        tool_purchase.save(update_fields=["paid"])

                        # Send push notification
                        send_push_notifications(
                            recipient=tool_purchase.seller.user,  # type: ignore
                            notification_type=Notification.JOB,
                            title="Tool Purchase",
                            body="A tool has been purchased from you.",
                        )
                    elif item_type == ItemType.JOB.value:
                        # check job initial payment to complete payment
                        job = get_object_or_404(JobInitialPayment, transaction_reference=transaction_ref)
                        job.paid = True
                        job.save(update_fields=["paid"])

                        # Send push notification
                        send_push_notifications(
                            recipient=job.job.client.user,  # type: ignore
                            notification_type=Notification.JOB,
                            title="Job Initial Payment",
                            body="A job initial payment has been made.",
                        )

                    else:
                        print("Invalid transaction reference")
        except (ValueError, KeyError) as exc:
            # Invalid payload
            print(str(exc))

        return SuccessResponse(status=status.HTTP_200_OK, message="Webhook received successfully.")
        # return Response(status=status.HTTP_200_OK)


class BanksListView(APIView):
    serializer_class = BankSerializer

    @extend_schema(
        operation_id="banks_list",
        parameters=FILTER_PARAMS,
        responses={
            200: OpenApiResponse(
                response=serializer_class(many=True),
                description="Resource fetched successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Payments"],
        description="Fetch banks list",
    )
    def get(self, request):
        query = request.GET.get("q", "*")  # search query
        order = request.GET.get("order", "asc")  # sorting order
        page = request.GET.get("page", 1)  # page number
        limit = request.GET.get("limit", settings.DEFAULT_PAGE_SIZE)  # limit per page

        queries = Q()

        if query != "*":
            queries &= Q(name__icontains=query) | Q(slug__icontains=query) | Q(code__icontains=query)

        banks = Bank.objects.filter(queries).order_by("name" if order == "asc" else "-name")
        count = banks.count()

        # Checking that the limit is not set to all to paginate
        if limit != "all":
            paginator = Paginator(banks, int(limit))
            banks = paginator.get_page(int(page))

        serializer = self.serializer_class(banks, many=True)
        data = add_count(serializer.data, count)
        return SuccessResponse(status=status.HTTP_200_OK, data=data)
