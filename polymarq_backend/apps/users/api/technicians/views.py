from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django_rest_passwordreset.serializers import PasswordTokenSerializer
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from polymarq_backend.apps.jobs.serializers import TechnicianSearchSerializer
from polymarq_backend.apps.users.api.serializers import (
    ErrorResponseSerializer,
    SuccessResponseSerializer,
    TechnicianCreateSerializer,
    TechnicianPhonePasswordCreateSerializer,
    TechnicianReadSerializer,
    TechniciansResponseCountSerializer,
    TechnicianTypesCountSerializer,
    TechnicianTypeSerializer,
    TechnicianUpdateSerializer,
)
from polymarq_backend.apps.users.models import Technician, TechnicianType, VerificationCode
from polymarq_backend.apps.users.utils import get_custom_user_model
from polymarq_backend.core.decorators import client_required, technician_required
from polymarq_backend.core.error_response import ErrorResponse
from polymarq_backend.core.sender import Sender
from polymarq_backend.core.success_response import SuccessResponse
from polymarq_backend.core.utils import add_count

User = get_custom_user_model()


class TechnicianRegistrationView(APIView):
    serializer_class = TechnicianCreateSerializer
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
        tags=["Technicians"],
        description="Register a new technician",
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            technician = serializer.save()

            # create OTP code for user email verification and send email
            verification_code = VerificationCode.objects.create(user=technician.user)

            context = {
                "user": technician.user,
                "verification_code": verification_code.code,
            }

            Sender(
                technician.user,
                email_content_object="notification.messages.user_registration",
                html_template="emails/authentication/user-verification.html",
                email_notif=True,
                context=context,
            )

            return SuccessResponse(
                message="Technician registered successfully",
                status=status.HTTP_201_CREATED,
            )
        else:
            return ErrorResponse(details=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TechnicianRegistrationPhoneView(APIView):
    """
    Register a new client - with phone number. Account type is individual
    """

    serializer_class = TechnicianPhonePasswordCreateSerializer
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
        tags=["Technicians"],
        description="Register a new technician - with phone number.",
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            # create technician
            serializer.save()

            return SuccessResponse(
                message="Techncian registered successfully",
                status=status.HTTP_201_CREATED,
            )
        return ErrorResponse(
            details=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class TechnicianListView(APIView):
    read_serializer_class = TechnicianReadSerializer

    @extend_schema(
        operation_id="technician_list",
        responses={
            200: OpenApiResponse(
                response=TechniciansResponseCountSerializer,
                description="Fetched successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Technicians"],
        description="Fetch all technicians",
    )
    def get(self, request):
        page = request.GET.get("page", 1)
        order = request.GET.get("order", "desc")
        order_by = request.GET.get("order_by", "updated_at")
        limit = request.GET.get("limit", settings.DEFAULT_PAGE_SIZE)

        queryset = Technician.objects.filter(is_deleted=False)
        obj_list = queryset.order_by(order_by if order == "asc" else f"-{order_by}")

        if limit != "all":
            pagination = Paginator(obj_list, int(limit))
            obj_list = pagination.get_page(int(page))

        serialized_list = self.read_serializer_class(obj_list, many=True, context={"request": request})
        data = add_count(serialized_list.data, queryset.count())
        return SuccessResponse(data=data, status=status.HTTP_200_OK)


class TechnicianDetailView(APIView):
    serializer_class = TechnicianUpdateSerializer
    read_serializer_class = TechnicianReadSerializer

    @extend_schema(
        operation_id="technician_detail",
        responses={
            200: OpenApiResponse(
                response=read_serializer_class,
                description="Fetched successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Technicians"],
        description="Fetch a technician's profile by ID",
    )
    def get(self, request, uuid):
        technician_obj = get_object_or_404(Technician, uuid=uuid, is_deleted=False)
        serializer = self.read_serializer_class(technician_obj, context={"request": request})
        return SuccessResponse(data=serializer.data, status=status.HTTP_200_OK)


class TechniciansNearbyView(APIView):
    serializer_class = TechnicianSearchSerializer

    @extend_schema(
        operation_id="technician_nearby",
        responses={
            200: OpenApiResponse(
                response=serializer_class,
                description="Fetched successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Technicians"],
        description="Fetch all technicians nearby",
    )
    @client_required()
    def get(self, request):
        page = request.GET.get("page", 1)
        order = request.GET.get("order", "desc")
        order_by = request.GET.get("order_by", "updated_at")
        limit = request.GET.get("limit", settings.DEFAULT_PAGE_SIZE)

        queryset = Technician.objects.filter(is_deleted=False)
        obj_list = queryset.order_by(order_by if order == "asc" else f"-{order_by}")

        if limit != "all":
            pagination = Paginator(obj_list, int(limit))
            obj_list = pagination.get_page(int(page))

        serialized_list = self.serializer_class(obj_list, many=True, context={"request": request})
        sorted_distance_list = sorted(
            serialized_list.data,
            key=lambda k: (k["distance_from_client"] if k["distance_from_client"] is not None else float("inf"),),
        )
        data = add_count(sorted_distance_list, queryset.count())
        return SuccessResponse(data=data, status=status.HTTP_200_OK)


class AuthorizedTechnicianDetailView(APIView):
    serializer_class = TechnicianUpdateSerializer
    read_serializer_class = TechnicianReadSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="authorized_technician_detail",
        responses={
            200: OpenApiResponse(
                response=read_serializer_class,
                description="Fetched successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Technicians"],
        description="Fetch a technician's profile by ID",
    )
    @technician_required
    def get(self, request):
        user = request.user
        technician_obj = get_object_or_404(Technician, user=user, is_deleted=False)
        serializer = self.read_serializer_class(technician_obj, context={"request": request})
        return SuccessResponse(data=serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=serializer_class,
        responses={
            202: OpenApiResponse(
                response=read_serializer_class,
                description="Updated successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Technicians"],
        description="Update a Technician's profile by ID",
    )
    @technician_required
    def patch(self, request):
        user = request.user
        technician_obj = get_object_or_404(Technician, user=user, is_deleted=False)

        serializer = self.serializer_class(
            technician_obj,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():
            serializer.save()
            response_data = self.read_serializer_class(serializer.instance, context={"request": request}).data
            return SuccessResponse(data=response_data, status=status.HTTP_202_ACCEPTED)

        return ErrorResponse(details=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        request=PasswordTokenSerializer,
        responses={
            204: OpenApiResponse(
                description="Deleted successfully",
            ),
            404: ErrorResponseSerializer,
        },
        tags=["Technicians"],
        description="Delete a Technician's profile. Note that `password` is required as a request body.",
    )
    @technician_required
    def delete(self, request):
        user = request.user

        # Validate password
        if not user.check_password(request.data.get("password")):
            return ErrorResponse(status=status.HTTP_403_FORBIDDEN, message="Invalid password")

        technician_obj = get_object_or_404(Technician, user=user)
        technician_obj.is_deleted = True
        technician_obj.save(update_fields=["is_deleted"])
        return SuccessResponse(status=status.HTTP_204_NO_CONTENT)


class TechnicianTypeView(APIView):
    serializer_class = TechnicianTypeSerializer

    @extend_schema(
        operation_id="technician_type_list",
        responses={
            200: OpenApiResponse(
                response=TechnicianTypesCountSerializer,
                description="Fetched successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Technician Types"],
        description="Fetch all technician types",
    )
    def get(self, request):
        types = TechnicianType.objects.all()
        serialized = self.serializer_class(types, many=True)
        data = add_count(serialized.data, types.count())
        return SuccessResponse(data=data, status=status.HTTP_200_OK)

    @extend_schema(
        request=serializer_class,
        responses={
            201: OpenApiResponse(
                response=serializer_class,
                description="Fetched successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Technician Types"],
        description="Create a technician type",
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return SuccessResponse(data=serializer.data, status=status.HTTP_201_CREATED)

        return ErrorResponse(details=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TechnicianTypeDetail(APIView):
    serializer_class = TechnicianTypeSerializer

    @extend_schema(
        operation_id="technician_type_detail",
        responses={
            200: OpenApiResponse(
                response=serializer_class,
                description="Fetched successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Technician Types"],
        description="Fetch a technician type by ID",
    )
    def get(self, request, uuid):
        type_obj = get_object_or_404(TechnicianType, uuid=uuid)
        serializer = self.serializer_class(type_obj)
        return SuccessResponse(data=serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=serializer_class,
        responses={
            202: OpenApiResponse(
                response=serializer_class,
                description="Updated successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Technician Types"],
        description="Update a Technician Type by ID",
    )
    def patch(self, request, uuid):
        type_obj = get_object_or_404(TechnicianType, uuid=uuid)

        serializer = self.serializer_class(
            type_obj,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():
            serializer.save()
            return SuccessResponse(data=serializer.data, status=status.HTTP_202_ACCEPTED)

        return ErrorResponse(details=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        responses={
            204: OpenApiResponse(
                description="Deleted successfully",
            ),
            404: ErrorResponseSerializer,
        },
        tags=["Technician Types"],
        description="Delete a Technician Type by ID",
    )
    def delete(self, request, uuid):
        type_obj = get_object_or_404(TechnicianType, uuid=uuid)
        type_obj.delete()
        return SuccessResponse(status=status.HTTP_204_NO_CONTENT)
