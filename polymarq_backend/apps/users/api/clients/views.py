from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django_rest_passwordreset.serializers import PasswordTokenSerializer
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from polymarq_backend.apps.users.api.serializers import (
    ClientCreateSerializer,
    ClientPhonePasswordCreateSerializer,
    ClientReadSerializer,
    ClientsResponseCountSerializer,
    ClientUpdateSerializer,
    ErrorResponseSerializer,
    SuccessResponseSerializer,
)
from polymarq_backend.apps.users.models import Client, VerificationCode
from polymarq_backend.apps.users.utils import get_custom_user_model
from polymarq_backend.core.decorators import client_required
from polymarq_backend.core.error_response import ErrorResponse
from polymarq_backend.core.sender import Sender
from polymarq_backend.core.success_response import SuccessResponse
from polymarq_backend.core.utils import add_count

User = get_custom_user_model()


class ClientRegistrationView(APIView):
    serializer_class = ClientCreateSerializer
    # allow any user (authenticated or not) to register
    permission_classes = [AllowAny]

    @extend_schema(
        request=serializer_class,
        responses={
            201: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="User registered successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Clients"],
        description="Register a new client",
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            # create client
            client = serializer.save()

            # create OTP code for user email verification and send email
            verification_code = VerificationCode.objects.create(user=client.user)

            context = {"user": client.user, "verification_code": verification_code.code}

            Sender(
                client.user,
                email_content_object="notification.messages.user_registration",
                html_template="emails/authentication/user-verification.html",
                email_notif=True,
                context=context,
            )

            return SuccessResponse(message="Client registered successfully", status=status.HTTP_201_CREATED)
        return ErrorResponse(
            details=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class ClientRegistrationPhoneView(APIView):
    """
    Register a new client - with phone number. Account type is individual
    """

    serializer_class = ClientPhonePasswordCreateSerializer
    # allow any user (authenticated or not) to register
    permission_classes = [AllowAny]

    @extend_schema(
        request=serializer_class,
        responses={
            201: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="User registered successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Clients"],
        description="Register a new client - with phone number. Account type is individual",
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            # create client
            serializer.save()

            return SuccessResponse(message="Client registered successfully", status=status.HTTP_201_CREATED)
        return ErrorResponse(
            details=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class ClientListView(APIView):
    read_serializer_class = ClientReadSerializer

    @extend_schema(
        operation_id="clients_list",
        responses={
            200: OpenApiResponse(
                response=ClientsResponseCountSerializer,
                description="Fetched successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Clients"],
        description="Fetch all clients",
    )
    def get(self, request):
        page = request.GET.get("page", 1)
        order = request.GET.get("order", "desc")
        order_by = request.GET.get("order_by", "updated_at")
        limit = request.GET.get("limit", settings.DEFAULT_PAGE_SIZE)

        queryset = Client.objects.filter(is_deleted=False)
        obj_list = queryset.order_by(order_by if order == "asc" else f"-{order_by}")

        if limit != "all":
            pagination = Paginator(obj_list, int(limit))
            obj_list = pagination.get_page(int(page))

        serialized_list = self.read_serializer_class(obj_list, many=True, context={"request": request})
        data = add_count(serialized_list.data, queryset.count())

        return SuccessResponse(data=data, message="Fetched successfully", status=status.HTTP_200_OK)


class ClientDetailView(APIView):
    serializer_class = ClientUpdateSerializer
    read_serializer_class = ClientReadSerializer

    @extend_schema(
        operation_id="client_detail",
        responses={
            200: OpenApiResponse(
                response=read_serializer_class,
                description="Fetched successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Clients"],
        description="Fetch a client's profile by UUID",
    )
    def get(self, request, uuid):
        client_obj = get_object_or_404(Client, uuid=uuid, is_deleted=False)
        serializer = self.read_serializer_class(client_obj, context={"request": request})
        return SuccessResponse(
            data=serializer.data,
            message="Fetched successfully",
            status=status.HTTP_200_OK,
        )


class AuthorizedClientDetailView(APIView):
    serializer_class = ClientUpdateSerializer
    read_serializer_class = ClientReadSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="authorized_client_detail_get",
        responses={
            200: OpenApiResponse(
                response=read_serializer_class,
                description="Fetched successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Clients"],
        description="Fetch a client's profile",
    )
    @client_required()
    def get(self, request):
        user = request.user
        client_obj = get_object_or_404(Client, user=user, is_deleted=False)
        serializer = self.read_serializer_class(client_obj, context={"request": request})
        return SuccessResponse(
            data=serializer.data,
            message="Fetched successfully",
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="authorized_client_detail_patch",
        request=serializer_class,
        responses={
            202: OpenApiResponse(
                response=read_serializer_class,
                description="Updated successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Clients"],
        description="Update a Techinician's profile",
    )
    @client_required()
    def patch(self, request):
        user = request.user
        client_obj = get_object_or_404(Client, user=user, is_deleted=False)

        serializer = self.serializer_class(
            client_obj,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():
            serializer.save()
            response_data = self.read_serializer_class(serializer.instance, context={"request": request}).data
            return SuccessResponse(
                data=response_data,
                message="Data updated successfully",
                status=status.HTTP_202_ACCEPTED,
            )
        return ErrorResponse(details=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        request=PasswordTokenSerializer,
        responses={
            204: OpenApiResponse(
                description="Deleted successfully",
            ),
            404: ErrorResponseSerializer,
        },
        tags=["Clients"],
        description="Delete a Client's profile. Note that `password` is required as a request body.",
    )
    @client_required()
    def delete(self, request):
        user = request.user

        # Validate password
        if not user.check_password(request.data.get("password")):
            return ErrorResponse(status=status.HTTP_403_FORBIDDEN, message="Invalid password")

        client_obj = get_object_or_404(Client, user=user)
        client_obj.is_deleted = True
        client_obj.save()
        return SuccessResponse(
            status=status.HTTP_204_NO_CONTENT,
        )
