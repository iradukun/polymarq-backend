from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiTypes  # type: ignore
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView

from polymarq_backend.apps.notifications.models import Notification
from polymarq_backend.apps.notifications.utils import send_push_notifications
from polymarq_backend.apps.payments.models import TechnicianBankAccount, ToolPurchase
from polymarq_backend.apps.payments.paystack.constants import ItemType
from polymarq_backend.apps.payments.paystack.services import Paystack
from polymarq_backend.apps.payments.serializers import ToolPurchaseSerializer
from polymarq_backend.apps.tools.models import RentalRequest, Tool, ToolCategory, ToolNegotiation
from polymarq_backend.apps.tools.serializers import (
    RentalRequestCountResponseSerializer,
    RentalRequestCreateSerializer,
    RentalRequestReadSerializer,
    RentalRequestUpdateSerializer,
    ToolCategoryResponseCountSerializer,
    ToolCategorySerializer,
    ToolCreateSerializer,
    ToolNegotiationCreateSerializer,
    ToolNegotiationReadSerializer,
    ToolNegotiationResponseSerializer,
    ToolReadSerializer,
    ToolsResponseCountSerializer,
    ToolUpdateSerializer,
)
from polymarq_backend.apps.tools.utils import TOOLS_CATEGORY_PARAMS, TOOLS_PARAMS
from polymarq_backend.apps.users.api.serializers import ErrorResponseSerializer
from polymarq_backend.apps.users.models import Technician
from polymarq_backend.apps.users.types import UserType
from polymarq_backend.core.decorators import client_or_technician_required, technician_required

# from polymarq_backend.core.sender import Sender
from polymarq_backend.core.success_response import SuccessResponse, SuccessResponseSerializer
from polymarq_backend.core.utils.main import add_count


class ToolCategoryView(APIView):
    """
    Enables Creation and Fetching a list of tools categories
    """

    serializer_class = ToolCategorySerializer

    @extend_schema(
        operation_id="tool_category_list",
        parameters=TOOLS_CATEGORY_PARAMS,
        responses={
            200: OpenApiResponse(
                response=ToolCategoryResponseCountSerializer,
                description="Resource fetched successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Tools"],
        description="Fetch all tool categories",
    )
    def get(self, request):
        query = request.GET.get("q", "*")  # search query
        order_by = request.GET.get("order_by", "name")  # field to order the dataset by
        order = request.GET.get("order", "asc")  # sorting order
        my_tools = (
            request.GET.get("my_tools", "false").lower() == "true"
        )  # filter by the current user's (technician) created tools
        page = request.GET.get("page", 1)  # page number
        limit = request.GET.get("limit", settings.DEFAULT_PAGE_SIZE)  # limit per page

        categories = ToolCategory.objects.prefetch_related("tools").filter(
            Q(name__icontains=query) | Q(description__icontains=query) if query != "*" else Q()
        )
        ordered_categories, count = (
            categories.order_by(order_by if order == "asc" else f"-{order_by}"),
            categories.count(),
        )
        my_tools_category_ids = Tool.objects.filter(owner__user=request.user, is_deleted=False).values_list(
            "category_id", flat=True
        )
        if my_tools:
            ordered_categories = ordered_categories.filter(id__in=my_tools_category_ids)

        # Checking that the limit is not set to all to paginate
        if limit != "all":
            paginator = Paginator(ordered_categories, int(limit))
            ordered_categories = paginator.get_page(int(page))

        serializer = self.serializer_class(ordered_categories, many=True)
        data = add_count(serializer.data, count)
        return SuccessResponse(data=data, status=status.HTTP_200_OK)

    # NOTE: This is commented out because we don't need to create tool categories
    # @extend_schema(
    #     request=serializer_class,
    #     responses={
    #         201: OpenApiResponse(
    #             response=SuccessResponseSerializer,
    #             description="Resource created successfully.",
    #         ),
    #         400: ErrorResponseSerializer,
    #     },
    #     tags=["Tools"],
    #     description="Create a new tool category",
    # )
    # @technician_required
    # def post(self, request):
    #     serializer = self.serializer_class(data=request.data)  # serializing request payload for the new category
    #     serializer.is_valid(raise_exception=True)
    #     serializer.save(created_by=request.user)
    #     return SuccessResponse(data=serializer.data, status=status.HTTP_201_CREATED)


class CreateToolView(APIView):
    """
    Enables creation of tools
    """

    serializer_class = ToolCreateSerializer
    read_serializer_class = ToolReadSerializer
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        operation_id="tool_create",
        request=serializer_class,
        responses={
            201: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Tool created successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Tools"],
        description="Create a new tool",
    )
    @technician_required
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        technician = get_object_or_404(Technician, user=request.user.pk)
        serializer.save(owner=technician)
        data = self.read_serializer_class(serializer.instance).data
        return SuccessResponse(status=201, data=data, message="Tool created successfully.")


class ToolsListView(APIView):
    """
    Searching and listing of available tools
    """

    serializer_class = ToolCreateSerializer
    read_serializer_class = ToolReadSerializer

    @extend_schema(
        operation_id="tool_list",
        parameters=TOOLS_PARAMS,  # type: ignore
        responses={
            200: OpenApiResponse(
                response=ToolsResponseCountSerializer,
                description="Resource fetched successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Tools"],
        description="Fetch all tools",
    )
    @client_or_technician_required
    def get(self, request):
        query = request.GET.get("q", "*")  # search query
        order_by = request.GET.get("order_by", "name")  # field to order the dataset by
        order = request.GET.get("order", "asc")  # sorting order
        page = request.GET.get("page", 1)  # page number
        my_tools = (
            request.GET.get("my_tools", "false").lower() == "true"
        )  # filter by the current user's (technician) created tools
        others_tools = (
            request.GET.get("others_tools", "false").lower() == "true"
        )  # filter by tools created by other technicians
        limit = request.GET.get("limit", settings.DEFAULT_PAGE_SIZE)  # limit per page
        category_uuid = request.GET.get("category", None)  # filter by category
        owner_uuid = request.GET.get("owner", None)  # filter by tool's owner (Technician)

        filter_query = (
            Q(name__icontains=query) | Q(category__name__icontains=query) | Q(description__icontains=query)
            if query != "*"
            else Q()
        )

        # Conditionally filter tools by category
        if category_uuid:
            filter_query &= Q(category__uuid=category_uuid)

        # Conditionally filter by owner's uuid
        if owner_uuid:
            filter_query &= Q(owner__uuid=owner_uuid)

        if my_tools:
            filter_query &= Q(owner__user=request.user)

        if others_tools:
            filter_query &= ~Q(owner__user=request.user)

        tools = Tool.objects.filter(filter_query, is_deleted=False, is_available=True, is_rented=False)
        ordered_tools, count = (
            tools.order_by(order_by if order == "asc" else f"-{order_by}"),
            tools.count(),
        )

        # Checking that the limit is not set to all to paginate
        if limit != "all":
            paginator = Paginator(ordered_tools, int(limit))
            ordered_tools = paginator.get_page(int(page))

        serializer = self.read_serializer_class(ordered_tools, many=True)
        data = add_count(serializer.data, count=count)

        return SuccessResponse(status=200, data=data)


class ToolsDetailView(APIView):
    serializer_class = ToolUpdateSerializer
    read_serializer_class = ToolReadSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_parser_classes(self):
        if self.request.method == "PATCH":
            return [MultiPartParser()]
        return [JSONParser()]

    @extend_schema(
        operation_id="tool_detail",
        responses={
            200: OpenApiResponse(
                response=read_serializer_class,
                description="Resource fetched successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Tools"],
        description="Fetch a tool by id",
    )
    @technician_required
    def get(self, request, uuid):
        tool = get_object_or_404(Tool, uuid=uuid, is_deleted=False)
        serializer = self.read_serializer_class(tool)
        return SuccessResponse(status=status.HTTP_200_OK, data=serializer.data)

    @extend_schema(
        operation_id="tool_detail_patch",
        # request=serializer_class,
        request={"multipart/form-data": serializer_class},
        responses={
            202: OpenApiResponse(
                response=read_serializer_class,
                description="Tool updated successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Tools"],
        description="Update a tool by id",
    )
    @technician_required
    def patch(self, request, uuid):
        tool = get_object_or_404(Tool, uuid=uuid, is_deleted=False)

        serializer = self.serializer_class(tool, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        data = self.read_serializer_class(serializer.instance).data

        return SuccessResponse(
            status=status.HTTP_202_ACCEPTED,
            data=data,
            message="Tool updated successfully.",
        )

    @extend_schema(
        responses={
            204: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Resource deleted successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Tools"],
        description="Delete a tool by id",
    )
    @technician_required
    def delete(self, request, uuid):
        tool = get_object_or_404(Tool, uuid=uuid, is_deleted=False)
        tool.is_deleted = True
        tool.save()
        return SuccessResponse(status=status.HTTP_204_NO_CONTENT, message="Tool deleted successfully.")


class ToolRentalRequestView(APIView):
    """
    Enables creation of rental request for a tool
    """

    serializer_class = RentalRequestCreateSerializer
    read_serializer_class = RentalRequestReadSerializer

    @extend_schema(
        operation_id="tool_rental_request",
        request=serializer_class,
        responses={
            201: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Rent requested successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Tools"],
        description="Rent a tool",
    )
    @technician_required
    def post(self, request):
        technician = get_object_or_404(Technician, user=request.user)
        serializer = self.serializer_class(data=request.data, user=technician)
        serializer.is_valid(raise_exception=True)
        serializer.save(request_owner=technician)

        recipient = (
            serializer.instance.tool.owner.user  # type: ignore
        )  # Using the tool's owner as the notification's recipient

        # Send push notification
        send_push_notifications(
            recipient=recipient,
            notification_type=Notification.TOOL_RENTAL,
            title="Tool Rental Request",
            body="A technician has just placed a rental request on your tool.\
                          Please check your dashboard for more info.",
        )

        data = self.read_serializer_class(serializer.instance).data
        return SuccessResponse(status=status.HTTP_201_CREATED, data=data)


class ToolRentalDetailView(APIView):
    """
    Enables a read, update and delete operation on a placed rental request.
    """

    serializer_class = RentalRequestUpdateSerializer
    read_serializer_class = RentalRequestReadSerializer

    @extend_schema(
        operation_id="tool_rental_request_detail",
        responses={
            200: OpenApiResponse(
                response=read_serializer_class,
                description="Resource fetched successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Tools"],
        description="Fetch a rental request by id",
    )
    @technician_required
    def get(self, request, uuid):
        obj = get_object_or_404(RentalRequest, uuid=uuid, is_deleted=False)
        serializer = self.read_serializer_class(instance=obj)
        return SuccessResponse(status=status.HTTP_200_OK, data=serializer.data)

    @extend_schema(
        operation_id="tool_rental_request_detail_patch",
        request=serializer_class,
        responses={
            202: OpenApiResponse(
                response=read_serializer_class,
                description="Resource updated successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Tools"],
        description="Update a rental request by id",
    )
    @technician_required
    def patch(self, request, uuid):
        obj = get_object_or_404(RentalRequest, uuid=uuid, is_deleted=False)
        serializer = self.serializer_class(instance=obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        data = self.read_serializer_class(serializer.instance).data
        return SuccessResponse(status=status.HTTP_202_ACCEPTED, data=data)

    @extend_schema(
        operation_id="tool_rental_request_detail_delete",
        responses={
            204: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Resource deleted successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Tools"],
        description="Delete a rental request by id",
    )
    @technician_required
    def delete(self, request, uuid):
        obj = get_object_or_404(RentalRequest, uuid=uuid, is_deleted=False)
        obj.is_deleted = True
        obj.save()
        return SuccessResponse(status=status.HTTP_204_NO_CONTENT)


class ToolRentalRequestListView(APIView):
    """
    Enables a listing of all the rental requests placed on a tool
    """

    serializer_class = RentalRequestReadSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="uuid",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Tool's UUID",
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=RentalRequestCountResponseSerializer,
                description="Resource fetched successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Tools"],
        description="Fetch all rental requests for a tool",
    )
    def get(self, request, uuid):
        rental_requests = RentalRequest.objects.filter(tool__uuid=uuid, is_deleted=False)
        serializer = self.serializer_class(rental_requests, many=True)
        data = add_count(serializer.data, rental_requests.count())
        return SuccessResponse(status=status.HTTP_200_OK, data=data)


class ToolRentalRequestAcceptView(APIView):
    """
    Enables acceptance of rental request
    """

    serializer_class = RentalRequestReadSerializer

    @extend_schema(
        operation_id="tool_rental_request_accept",
        parameters=[
            OpenApiParameter(
                name="uuid",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Request's UUID",
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Request Accepted succesfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Tools"],
        description="Accept a rental request",
    )
    def put(self, request, uuid):
        request_obj = get_object_or_404(RentalRequest, uuid=uuid, is_deleted=False)
        request_obj.request_status = RentalRequest.RequestStatus.ACCEPTED
        request_obj.save()

        # Send push notification
        recipient = request_obj.request_owner.user  # type: ignore

        send_push_notifications(
            recipient=recipient,  # type: ignore
            notification_type=Notification.TOOL_RENTAL,
            title="Tool Rental Request",
            body="Your request to rent a tool has been accepted.\
                Please check your dashboard for more info.",
        )

        return SuccessResponse(status=202, message="Request Accepted succesfully.")


class ToolRentalRequestDeclineView(APIView):
    """
    Enables rejection of rental request
    """

    serializer_class = RentalRequestReadSerializer

    @extend_schema(
        operation_id="tool_rental_request_decline",
        parameters=[
            OpenApiParameter(
                name="uuid",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Request's UUID",
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Request Declined succesfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Tools"],
        description="Decline a rental request",
    )
    def put(self, request, uuid):
        request_obj = get_object_or_404(RentalRequest, uuid=uuid, is_deleted=False)
        request_obj.request_status = RentalRequest.RequestStatus.REJECTED
        request_obj.save()

        # Send push notification
        recipient = request_obj.request_owner.user  # type: ignore
        send_push_notifications(
            recipient=recipient,  # type: ignore
            notification_type=Notification.TOOL_RENTAL,
            title="Tool Rental Request",
            body="Your request to rent a tool has been declined.\
                Please check your dashboard for more info.",
        )

        return SuccessResponse(status=202, message="Request Declined succesfully.")


class ToolNegotiationView(APIView):
    """
    Initiates a negotiation for a tool
    Gets all tools negotiations for tool's owner
    """

    serializer_class = ToolNegotiationCreateSerializer

    @extend_schema(
        operation_id="tool_negotiate",
        request=serializer_class,
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Negotiation submitted successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Tools"],
        description="Negotiate a tool",
    )
    @client_or_technician_required
    def post(self, request, *args, **kwargs):
        user: UserType = request.user

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        tool_uuid = serializer.validated_data.pop("tool_uuid")  # type: ignore
        offered_price = serializer.validated_data.pop("offered_price")  # type: ignore

        tool = get_object_or_404(Tool, uuid=tool_uuid, is_deleted=False)

        negotiation, created = ToolNegotiation.objects.get_or_create(
            negotiator=user,
            tool=tool,
            tool_owner=tool.owner,
            defaults={
                "offered_price": offered_price,
                "status": ToolNegotiation.PENDING,
            },
        )

        if not created and negotiation.status == "rejected" and negotiation.attempts < 3:
            negotiation.offered_price = offered_price
            negotiation.status = ToolNegotiation.PENDING
            negotiation.attempts += 1
            negotiation.save()

            # Send push notification
        send_push_notifications(
            recipient=tool.owner.user,  # type: ignore
            notification_type=Notification.TOOL_NEGOTIATION,
            title="Tool Negotiation",
            push_notif_data={
                "negotiation_uuid": str(negotiation.uuid),
                "price": float(offered_price),
            },  # type: ignore
            body=f"{user.first_name} {user.last_name} has just placed a negotiation on your tool.",
        )

        return SuccessResponse(status=status.HTTP_200_OK, message="Negotiation submitted successfully.")

    @extend_schema(
        operation_id="tool_negotiate_list",
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Negotiations fetched successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Tools"],
        description="Fetch all tool negotiations",
    )
    @technician_required
    def get(self, request, *args, **kwargs):
        user = request.user
        technician = user.technician
        negotiations = ToolNegotiation.objects.filter(tool_owner=technician, status=ToolNegotiation.PENDING)

        serializer = ToolNegotiationReadSerializer(negotiations, many=True)

        return SuccessResponse(
            status=status.HTTP_200_OK,
            data=serializer.data,
            message="Negotiations fetched successfully.",
        )


class ToolNegotiationResponseView(APIView):
    """
    Accepts or rejects a negotiation for a tool
    """

    serializer_class = ToolNegotiationResponseSerializer

    @extend_schema(
        operation_id="tool_negotiate_response",
        request=serializer_class,
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Negotiation response submitted successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Tools"],
        description="Respond to a tool negotiation",
    )
    @technician_required
    def post(self, request, *args, **kwargs):
        user = request.user

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        negotiation_uuid = serializer.validated_data.pop("negotiation_uuid")  # type: ignore
        negotiation_status = serializer.validated_data.pop("status")  # type: ignore

        negotiation = get_object_or_404(ToolNegotiation, uuid=negotiation_uuid, status=ToolNegotiation.PENDING)

        if negotiation.tool_owner.user != user:  # type: ignore
            return SuccessResponse(
                status=status.HTTP_403_FORBIDDEN,
                message="You are not authorized to respond to this negotiation.",
            )

        # create notification to negotiator about tool negotiation repsonse from tool owner
        send_push_notifications(
            recipient=negotiation.negotiator,  # type: ignore
            notification_type=Notification.TOOL_NEGOTIATION_RESPONSE,
            title="Tool Negotiation Response",
            body=f"{negotiation.tool_owner.user.first_name} {negotiation.tool_owner.user.last_name}"  # type: ignore
            "has just responded to your negotiation.",
        )

        negotiation.status = negotiation_status
        negotiation.save(update_fields=["status"])

        return SuccessResponse(status=status.HTTP_200_OK, message="Negotiation response submitted.")


class ToolPurchaseInitiateView(APIView):
    """Initiate purchasing a tool"""

    serializer_class = ToolPurchaseSerializer

    @extend_schema(
        operation_id="tool_purchase",
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Tool purchased successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Tools"],
        description="Purchase a tool",
    )
    @client_or_technician_required
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        buyer: UserType = request.user
        tool_uuid = serializer.validated_data.pop("tool_uuid")  # type: ignore
        # Get the Tool instance with the given uuid
        tool = get_object_or_404(Tool, uuid=tool_uuid)

        # check if tool has an accepted negotiation agreed upon by the buyer
        tool_negotiation = ToolNegotiation.objects.filter(
            tool=tool, negotiator=buyer, status=ToolNegotiation.ACCEPTED
        ).first()

        if tool_negotiation:
            tool_amount = float(tool_negotiation.offered_price.amount)
        else:
            tool_amount = float(tool.price.amount)

        # Get or create a ToolPurchase instance
        tool_purchase, created = ToolPurchase.objects.get_or_create(
            seller=tool_negotiation.tool_owner if tool_negotiation else tool.owner,  # type: ignore
            buyer=buyer,
            tool=tool,
            amount=tool_amount,
            defaults={"status": "initiated"},
        )

        # If the ToolPurchase instance was not created in this request, update the status
        if not created:
            tool_purchase.status = ToolPurchase.INITIATED
            tool_purchase.save()

        if tool_negotiation:
            try:
                technician_bank_info: TechnicianBankAccount = tool_negotiation.tool_owner.technician_bank_account  # type: ignore # noqa: E501
            except TechnicianBankAccount.DoesNotExist:
                raise serializers.ValidationError("Technician bank account not found")
        else:
            try:
                technician_bank_info: TechnicianBankAccount = tool.owner.technician_bank_account  # type: ignore
            except TechnicianBankAccount.DoesNotExist:
                raise serializers.ValidationError("Technician bank account not found")

        paystack = Paystack()
        # Initiate paystack payment transaction
        paystack_response = paystack.initiate_subaccount_transaction(
            user=tool.owner.user,  # type: ignore
            amount=serializer.validated_data["quantity"] * tool_amount,  # type: ignore
            subaccount_code=technician_bank_info.paystack_subaccount_code,  # type: ignore
            item_type=ItemType.TOOL,
        )

        # Send the authorization URL and the purchase to the frontend
        if paystack_response["status"]:  # type: ignore
            tool_purchase.transaction_reference = paystack_response["data"]["reference"]  # type: ignore
            tool_purchase.save(update_fields=["transaction_reference"])
            return SuccessResponse(
                status=status.HTTP_200_OK,
                data={
                    "authorization_url": paystack_response["data"]["authorization_url"],  # type: ignore
                    "purchase": serializer.data,
                },
                message="Tool purchase initiated successfully.",
            )
        else:
            return SuccessResponse(
                status=status.HTTP_400_BAD_REQUEST,
                data=paystack_response["message"],  # type: ignore
                message="Error initiating tool purchase.",
            )


class ToolsCountsView(APIView):
    """
    Enables fetching of tool counts
    """

    serializer_class = ToolCreateSerializer

    @extend_schema(
        operation_id="tool_counts",
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Tool counts fetched successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        parameters=[
            OpenApiParameter(
                name="my_tools",
                description="Filter by the current user's (technician) created tools",
                required=False,
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="others_tools",
                description="Filter by other technician created tools",
                required=False,
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
            ),
        ],
        tags=["Tools"],
        description="Fetch all tool counts",
    )
    @technician_required
    def get(self, request):
        my_tools = (
            request.GET.get("my_tools", "false").lower() == "true"
        )  # filter by the current user's (technician) created tools
        others_tools = (
            request.GET.get("others_tools", "false").lower() == "true"
        )  # filter by tools created by other technicians
        count = 0
        if my_tools:
            count = Tool.objects.filter(owner__user=request.user, is_deleted=False).count()

        if others_tools:
            count = Tool.objects.filter(~Q(owner__user=request.user), is_deleted=False).count()

        return SuccessResponse(status=status.HTTP_200_OK, data={"count": count})
