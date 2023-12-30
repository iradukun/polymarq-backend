from decimal import Decimal

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from djmoney.money import Money
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

# from polymarq_backend.apps.aws_sns.models import Device
# from polymarq_backend.apps.aws_sns.tasks import refresh_device
from polymarq_backend.apps.jobs.models import Job, Ping
from polymarq_backend.apps.jobs.serializers import (
    CreatePingSerializer,
    InitialJobPaymentSerializer,
    JobCreateSerializer,
    JobReadSerializer,
    JobResponseCountSerializer,
    JobUpdateSerializer,
    PingReadSerializer,
    TechnicianSearchSerializer,
    UpdatePingSerializer,
)
from polymarq_backend.apps.notifications.models import Notification
from polymarq_backend.apps.notifications.utils import send_push_notifications
from polymarq_backend.apps.payments.models import JobInitialPayment, JobPriceQuotation, TechnicianBankAccount
from polymarq_backend.apps.payments.paystack.constants import ItemType
from polymarq_backend.apps.payments.paystack.services import Paystack
from polymarq_backend.apps.payments.services import PaymentService
from polymarq_backend.apps.users.api.serializers import ErrorResponseSerializer, SuccessResponseSerializer
from polymarq_backend.apps.users.models import Technician
from polymarq_backend.apps.users.utils import cherry_pick_params
from polymarq_backend.core.decorators import client_or_technician_required, client_required, technician_required
from polymarq_backend.core.error_response import ErrorResponse
from polymarq_backend.core.sender import Sender
from polymarq_backend.core.success_response import SuccessResponse
from polymarq_backend.core.utils.main import add_count, distance_between_two_points


class CreateJobView(APIView):
    """
    Allows only a Client to create a job
    """

    authentication_classes = [JWTAuthentication]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = JobCreateSerializer

    @extend_schema(
        request=serializer_class,
        responses={
            201: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Job created successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Jobs"],
        description="Used by a Client to create a new Job",
    )
    @client_required()
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return SuccessResponse(data=serializer.data, status=status.HTTP_201_CREATED)


class TechnicianSearchView(APIView):
    """
    Allows only a Client to search for a technician

    non-premium account:
    -   can only search a limited distance ( m)
    -   no search filters
    premium account:
    -   no limit on distance of the tecnician
    -   multiple search filters;
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = []  # Anyone can access this endpoint
    serializer_class = TechnicianSearchSerializer

    @extend_schema(
        operation_id="technician_search",
        parameters=[
            OpenApiParameter(
                name="page",
                description="Filtering page number",
                required=False,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="order",
                description="Order by 'asc' or 'desc'",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="order_by",
                description="Order by 'updated_at' or 'created_at'",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="limit",
                description="Limit number of results",
                required=False,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="job_uuid",
                description="Filter by job uuid",
                required=True,
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=serializer_class,
                description="Fetched successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Jobs"],
        description="Used by Client to find technicians",
    )
    def get(self, request):
        page = request.GET.get("page", 1)
        order = request.GET.get("order", "dist")  # dist, asc, desc
        order_by = request.GET.get("order_by", "updated_at")
        limit = request.GET.get("limit", settings.DEFAULT_PAGE_SIZE)
        job_uuid = request.GET.get("job_uuid", None)

        if not job_uuid:
            return ErrorResponse(status=400, message="job_uuid is required")

        # TODO
        # set max distance a person without premium account can cover
        # if request.user.is_client and request.user.is_active and request.user.is_verified:

        try:
            job = Job.objects.get(uuid=job_uuid)
        except Job.DoesNotExist:
            return ErrorResponse(status=404, message="Job not found")

        # check if technicians have been ping for this job previously in Ping model
        # if yes, then get the technicians that have been pinged
        pinged_technicians = Ping.objects.filter(job=job, status__in=[Ping.REQUESTED, Ping.DECLINED])

        # if pinged_technicians exist then this isn't the first ping cycle
        # so we get the technicians that have been pinged
        if pinged_technicians.exists():
            pinged_technicians_count = pinged_technicians.count()
            requested_technicians = pinged_technicians.filter(status=Ping.REQUESTED)
            declined_technicians = pinged_technicians.filter(status=Ping.DECLINED)

            # check if all the pinged technicians have declined the job
            # if yes, we recalculate the price quotations for the technicians and ping them again
            if pinged_technicians_count == declined_technicians.count():
                PaymentService.calculate_price_quotations(job, technicians=declined_technicians)
                pinged_technicians = declined_technicians
                pinged_technicians_count = declined_technicians.count()

            elif pinged_technicians_count == requested_technicians.count():
                # TODO: Handle situation when all pinged technicians have yet to respond to the ping
                pass

            else:
                # TODO: Handle situation when some pinged technicians have yet to respond to the ping
                pass

        else:
            # if pinged_technicians doesn't exist then this is the first ping cycle
            # so we calculate the price quotations for the technicians and ping them
            queryset = Technician.objects.filter(is_deleted=False)
            queryset_count = queryset.count()

            if order != "dist":
                queryset = queryset.order_by(order_by if order == "asc" else f"-{order_by}")

            if limit != "all":
                pagination = Paginator(queryset, int(limit))
                queryset = pagination.get_page(int(page))

            PaymentService.calculate_price_quotations(job, technicians=queryset)

            serialized_list = self.serializer_class(queryset, many=True, context={"request": request})

            if order == "dist":
                sorted_distance_list = sorted(
                    serialized_list.data,
                    key=lambda k: (
                        k["distance_from_client"] if k["distance_from_client"] is not None else float("inf"),
                    ),
                )
                data = add_count(sorted_distance_list, queryset_count)
            else:
                data = add_count(serialized_list.data, queryset_count)

            return SuccessResponse(data=data, status=status.HTTP_200_OK)


class CreatePingView(APIView):
    """
    Allows only a Client to Ping a technician
    """

    authentication_classes = [JWTAuthentication]
    serializer_class = CreatePingSerializer

    @extend_schema(
        request=serializer_class,
        responses={
            201: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Ping created successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Jobs"],
        description="Used by a Client to Ping a technician",
    )
    @client_required()
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        """
        TODO:
        1) no account —> create onebefore pininging but can view tech-eng around
        2) have account without payment details—> enter payment details before pinging but can view tech-eng
        3) account wit payment details entered in profil (no premium account) —> ping 3
        4) premium account —/-> more then 3
        """

        # Limit max number of creatable Pings to 3
        if Ping.objects.filter(client__user=self.request.user, status="REQUESTED").count() > 2:
            return ErrorResponse(
                status=400,
                message="Maximum number of pings reached. Wait till "
                "one of your pings is accepted or declined before trying again.",
            )

        # Calculate and store the distance between the client and the technician
        # automatically in the backend

        technician_uuid = serializer.validated_data.pop("technician_uuid", None)  # type: ignore
        job_uuid = serializer.validated_data.pop("job_uuid", None)  # type: ignore

        try:
            technician = Technician.objects.get(uuid=technician_uuid)
        except Technician.DoesNotExist:
            return ErrorResponse(status=404, message="Technician not found")

        distance_from_client = distance_between_two_points(
            self.request.user.longitude,  # type: ignore
            self.request.user.latitude,  # type: ignore
            technician.user.longitude,  # type: ignore
            technician.user.latitude,  # type: ignore
        )

        try:
            job = Job.objects.get(uuid=job_uuid)
        except Job.DoesNotExist:
            return ErrorResponse(status=404, message="Job not found")

        try:
            job_price_quotation = JobPriceQuotation.objects.get(job=job, technician=technician)
            job_price_quote = job_price_quotation.price
        except JobPriceQuotation.DoesNotExist:
            job_price_quote = PaymentService.calculate_price_quotation(job=job, technician=technician)

        serializer.save(
            distance_from_client=distance_from_client,
            price_quote=job_price_quote,
            job=job,
            technician=technician,
        )

        # Send email notification
        context = {"user": technician.user}
        Sender(
            user_account=technician.user,
            email_content_object="notification.messages.ping_technician",
            html_template="emails/job/ping_technician.html",
            context=context,
            email_notif=True,
        )

        # Send push notification
        send_push_notifications(
            recipient=technician.user,  # type: ignore
            notification_type=Notification.JOB,
            title="Job Request",
            body="A client has just requested your services. \
                Please check your dashboard for more info.\
                Also note that you have 24 hours to respond, \
                else the request will be declined automatically",
        )

        return SuccessResponse(data=serializer.data, status=status.HTTP_201_CREATED)


class UpdatePingView(APIView):
    """
    Allows only a technician to accept or decline a Ping
    """

    authentication_classes = [JWTAuthentication]
    serializer_class = UpdatePingSerializer

    @extend_schema(
        request=serializer_class,
        responses={
            201: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Updated successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Jobs"],
        description="Used by a Technician to accept or decline a Ping",
    )
    @technician_required
    def patch(self, request, uuid):
        # get unexpired ping
        ping_obj = get_object_or_404(Ping, ~Q(status="EXPIRED"), uuid=uuid)

        new_status = request.data.get("status")
        if new_status == ping_obj.status:
            return ErrorResponse(status=400, message="Job is already in the desired state.")

        serializer = self.serializer_class(
            ping_obj,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        context = {"user": ping_obj.client.user, "technician": ping_obj.technician}

        if serializer.data.get("status") == Ping.ACCEPTED:
            # make other pings for this job expired
            Ping.objects.filter(job=ping_obj.job).exclude(uuid=ping_obj.uuid).update(status=Ping.EXPIRED)
            # set technician for job
            ping_obj.job.technician = ping_obj.technician
            ping_obj.job.status = Job.IN_PROGRESS
            ping_obj.job.save(update_fields=["technician"])
            # Send email notification
            Sender(
                user_account=ping_obj.client.user,
                email_content_object="notification.messages.accept_or_decline",
                html_template="emails/job/accept.html",
                context=context,
                email_notif=True,
            )

            # Send push notification

            send_push_notifications(
                recipient=ping_obj.client.user,  # type: ignore
                notification_type=Notification.JOB,
                title="Job Request Accepted",
                body=f"{ping_obj.technician.user.username} has accepted your job request.",
            )

            return SuccessResponse(
                message="Job Request Accepted",
                data=serializer.data,
                status=status.HTTP_202_ACCEPTED,
            )

        elif serializer.data.get("status") == Ping.DECLINED:
            # Send email notification
            Sender(
                user_account=ping_obj.client.user,
                email_content_object="notification.messages.accept_or_decline",
                html_template="emails/job/decline.html",
                context=context,
                email_notif=True,
            )

            # Send push notification
            send_push_notifications(
                recipient=ping_obj.client.user,  # type: ignore
                notification_type=Notification.JOB,
                title="Job Request Declined",
                body=f"{ping_obj.technician.user.username} has declined your job request.",
            )

            return SuccessResponse(
                message="Job Request Declined",
                data=serializer.data,
                status=status.HTTP_202_ACCEPTED,
            )

        elif serializer.data.get("status") == Ping.NEGOTIATING:
            (
                recommended_min_price,
                recommended_max_price,
            ) = PaymentService.suggest_recommended_budget_range_from_technicians_responses(ping_obj.job)
            context["job_price_recommendation"] = {
                "min_price": recommended_min_price,
                "max_price": recommended_max_price,
            }
            # Send email notification
            Sender(
                user_account=ping_obj.client.user,
                email_content_object="notification.messages.accept_or_decline",
                html_template="emails/job/negotiating.html",
                context=context,
                email_notif=True,
            )

            # Send push notification
            send_push_notifications(
                recipient=ping_obj.client.user,  # type: ignore
                notification_type=Notification.JOB,
                title="Job Request Negotiated",
                body=f"{ping_obj.technician.user.username} is negotiating your job request. \
                        Recommended price range is {recommended_min_price} - {recommended_max_price}",
            )

        return SuccessResponse(
            data=serializer.data,
            message="Job Request Negotiated",
            status=status.HTTP_202_ACCEPTED,
        )


class ListJobView(APIView):
    """
    Fetch all available Jobs (that have not been taken/accepted)
    Technician or Client ONLY
    """

    authentication_classes = [JWTAuthentication]
    read_serializer_class = JobReadSerializer

    @extend_schema(
        operation_id="job_list",
        parameters=[
            OpenApiParameter(
                name="my_jobs",
                description="Filter by the current user's accepted jobs or not",
                required=False,
                type=bool,
            ),
            OpenApiParameter(
                name="order",
                description="Order by 'asc' or 'desc'",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="order_by",
                description="Order by 'updated_at' or 'created_at'",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="name",
                description="Filter by job name",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="client_username",
                description="Filter client username",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="client_first_name",
                description="Filter by client first name",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="client_last_name",
                description="Filter by last name",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="duration",
                description="Filter duration of the job (days)",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="name",
                description="Filter by job name",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="currency",
                description="Must be set to filter min_price or max_price by a currency,"
                + " different from NGN (which is the default), like USD etc.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="min_price",
                description="Filter by minimum price",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="max_price",
                description="Filter by maximum price",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="require_technicians_immediately",
                description="Filter by require technicians immediately",
                required=False,
                type=bool,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=JobResponseCountSerializer,
                description="Fetched successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Jobs"],
        description="Fetch all available Jobs (that have not been taken/accepted)",
    )
    @client_or_technician_required
    def get(self, request):
        [
            my_jobs,
            order,
            order_by,
            page_number,
            limit,
            name,
            client_username,
            client_first_name,
            client_last_name,
            duration,
            min_price,
            max_price,
            require_technicians_immediately,
            currency,
        ] = cherry_pick_params(
            request.query_params,
            [
                "my_jobs",
                "order",
                "order_by",
                "page_number",
                "limit",
                "name",
                "client_username",
                "client_first_name",
                "client_last_name",
                "duration",
                "min_price",
                "max_price",
                "require_technicians_immediately",
                "currency",
            ],
        )

        query = Q()
        query &= Q(is_deleted=False)

        if request.user.is_client is True:  # If client, return only the client jobs
            query &= Q(client__user=request.user)
        elif request.user.is_technician is True:
            if my_jobs == "true":  # Return the technician jobs
                query &= Q(technician__user=request.user)
            else:
                query &= Q(technician=None)  # Or default to available jobs

        if name:
            query &= Q(name__icontains=name)
        if client_username:
            query &= Q(client__user__username__icontains=client_username)
        if client_first_name:
            query &= Q(client__user__first_name__icontains=client_first_name)
        if client_last_name:
            query &= Q(client__user__last_name__icontains=client_last_name)
        if duration:
            query &= Q(duration=int(duration))
        if min_price:
            if not currency:
                currency = "NGN"
            query &= Q(min_price__gte=Money(Decimal(min_price), currency))
        if max_price:
            if not currency:
                currency = "NGN"
            query &= Q(max_price__lte=Money(Decimal(max_price), currency))
        if require_technicians_immediately == "true":
            query &= Q(require_technicians_immediately=True if require_technicians_immediately == "true" else False)
        if not order:
            order = "asc"
        if not order_by:
            order_by = "updated_at"

        order_by = order_by if order == "asc" else f"-{order_by}"
        queryset = Job.objects.filter(query).order_by(order_by)
        count = queryset.count()

        if limit != "all":
            pagination = Paginator(queryset, int(limit or settings.DEFAULT_PAGE_SIZE))
            queryset = pagination.get_page(int(page_number or 1))

        serialized_list = self.read_serializer_class(queryset, many=True, context={"request": request})
        data = add_count(serialized_list.data, count)

        return SuccessResponse(data=data, message="Fetched successfully", status=status.HTTP_200_OK)


class JobDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    # Using these parser classes because of the
    # image field when updating the job object
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = JobCreateSerializer
    update_serializer_class = JobUpdateSerializer

    @extend_schema(
        operation_id="job_detail",
        request=serializer_class,
        responses={
            202: OpenApiResponse(
                response=serializer_class,
                description="Fetched successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Jobs"],
        description="Fetch job detail",
    )
    @client_or_technician_required
    def get(self, request, uuid):
        """
        Retrieve a model instance.
        """
        instance = get_object_or_404(Job, uuid=uuid, is_deleted=False)
        serializer = self.serializer_class(instance)
        return SuccessResponse(
            data=serializer.data,
            message="Fetched successfully",
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="update_job",
        request=update_serializer_class,
        responses={
            202: OpenApiResponse(
                response=update_serializer_class,
                description="Updated successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Jobs"],
        description="Update Job",
    )
    @client_required()
    def patch(self, request, uuid):
        instance = get_object_or_404(Job, uuid=uuid, is_deleted=False)
        serializer = self.update_serializer_class(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(
            data=serializer.data,
            message="Data updated successfully",
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(
        operation_id="delete_job",
        responses={
            204: OpenApiResponse(
                description="Deleted successfully",
            ),
            404: ErrorResponseSerializer,
        },
        tags=["Jobs"],
        description="Delete a Job by uuid",
    )
    @client_required()
    def delete(self, request, uuid):
        instance = get_object_or_404(Job, uuid=uuid, is_deleted=False)
        instance.is_deleted = True
        instance.save()
        return SuccessResponse(status=status.HTTP_204_NO_CONTENT)


class JobRequests(APIView):
    serializer_class = PingReadSerializer

    @extend_schema(
        operation_id="job_requests",
        responses={
            200: OpenApiResponse(
                response=serializer_class,
                description="Fetched successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Jobs"],
        description="Fetch all job requests (pings) for the current user (technician)",
    )
    @technician_required
    def get(self, request):
        ping_queryset = (
            Ping.objects.select_related("job")
            .filter(technician__user=request.user, status=Ping.REQUESTED)
            .order_by("-created_at")
        )
        serialized_list = self.serializer_class(ping_queryset, many=True, context={"request": request})
        data = add_count(serialized_list.data, ping_queryset.count())
        return SuccessResponse(data=data, message="Fetched successfully", status=status.HTTP_200_OK)


class JobInitialPaymentInitiateView(APIView):
    """
    Allows only a Client to initiate a payment for a job
    """

    serializer_class = InitialJobPaymentSerializer

    @extend_schema(
        operation_id="job_initial_payment_initiate",
        responses={
            200: OpenApiResponse(
                response=serializer_class,
                description="Fetched successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Jobs"],
        description="Initiate payment for a job",
    )
    @client_required()
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        job_uuid = serializer.validated_data.pop("job_uuid")

        try:
            job = Job.objects.get(uuid=job_uuid)
        except Job.DoesNotExist:
            return ErrorResponse(status=404, message="Job not found")

        # get accepted job ping for this job
        try:
            ping = Ping.objects.get(job=job, status=Ping.ACCEPTED)
        except Ping.DoesNotExist:
            return ErrorResponse(status=404, message="No accepted job request found for this job")

        # initial amount is 50% of the price quote
        amount = float(ping.price_quote.amount / 2)

        # initiate payment
        job_initial_payment, _created = JobInitialPayment.objects.get_or_create(
            job=job,
            client=job.client,
            technician=ping.technician,
            amount=ping.price_quote.amount / 2,
            paid=False,
        )

        try:
            technician_bank_info: TechnicianBankAccount = ping.technician.technician_bank_account  # type: ignore
        except TechnicianBankAccount.DoesNotExist:
            raise serializers.ValidationError("Technician bank account not found")

        paystack = Paystack()
        # Initiate paystack payment transaction
        paystack_response = paystack.initiate_subaccount_transaction(
            user=ping.technician.user,  # type: ignore
            amount=amount,
            subaccount_code=technician_bank_info.paystack_subaccount_code,  # type: ignore
            item_type=ItemType.JOB,
        )

        # Send the authorization URL and the purchase to the frontend
        if paystack_response["status"]:  # type: ignore
            job_initial_payment.transaction_reference = paystack_response["data"]["reference"]  # type: ignore
            job_initial_payment.save(update_fields=["transaction_reference"])
            return SuccessResponse(
                status=status.HTTP_200_OK,
                data={
                    "authorization_url": paystack_response["data"]["authorization_url"],  # type: ignore
                    "purchase": serializer.data,
                },
                message="Payment initiated successfully",
            )
        else:
            return SuccessResponse(
                status=status.HTTP_400_BAD_REQUEST,
                data=paystack_response["message"],  # type: ignore
                message="Error initiating payment",
            )
