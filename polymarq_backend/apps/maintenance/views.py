from decimal import Decimal

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from djmoney.money import Money
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from polymarq_backend.apps.maintenance.models import Maintenance
from polymarq_backend.apps.maintenance.serializers import (
    MaintenanceCreateSerializer,
    MaintenanceReadSerializer,
    MaintenanceResponseCountSerializer,
    MaintenanceUpdateSerializer,
)
from polymarq_backend.apps.users.api.serializers import ErrorResponseSerializer, SuccessResponseSerializer
from polymarq_backend.apps.users.utils import cherry_pick_params
from polymarq_backend.core.decorators import client_or_technician_required, client_required
from polymarq_backend.core.success_response import SuccessResponse
from polymarq_backend.core.utils.main import add_count


class CreateMaintenanceView(APIView):
    """
    Allows only a Client to schedule a maintenance
    """

    authentication_classes = [JWTAuthentication]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = MaintenanceCreateSerializer

    @extend_schema(
        request=serializer_class,
        responses={
            201: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Maintenance created successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Maintenance"],
        description="Used by a Client to schedule a new Maintenance",
    )
    @client_required()
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return SuccessResponse(data=serializer.data, status=status.HTTP_201_CREATED)


class ListMaintenanceView(APIView):
    """
    Fetch all available Maintenance (that have not been taken/accepted)
    Technician or Client ONLY
    """

    authentication_classes = [JWTAuthentication]
    read_serializer_class = MaintenanceReadSerializer

    @extend_schema(
        operation_id="maintenance_list",
        parameters=[
            OpenApiParameter(
                name="my_maintenance",
                description="Filter by the current user's accepted maintenance or not",
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
                description="Filter by maintenance name",
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
                description="Filter duration of the maintenance (days)",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="name",
                description="Filter by maintenance name",
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
                response=MaintenanceResponseCountSerializer,
                description="Fetched successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Maintenance"],
        description="Fetch all available Maintenance (that have not been taken/accepted)",
    )
    @client_or_technician_required
    def get(self, request):
        [
            my_maintenance,
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
                "my_maintenance",
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

        if request.user.is_client is True:  # If client, return only the client maintenance
            query &= Q(client=request.user.client)
        elif request.user.is_technician is True:
            if my_maintenance == "True":  # Return the technician maintenance
                query &= Q(technician=request.user.technician)
            else:
                query &= Q(technician=None)  # Or default to available maintenance

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
        if require_technicians_immediately == "True":
            query &= Q(require_technicians_immediately=require_technicians_immediately)
        if not order:
            order = "asc"
        if not order_by:
            order_by = "updated_at"

        order_by = order_by if order == "asc" else f"-{order_by}"
        queryset = Maintenance.objects.filter(query).order_by(order_by)
        count = queryset.count()

        if limit != "all":
            pagination = Paginator(queryset, int(limit or settings.DEFAULT_PAGE_SIZE))
            queryset = pagination.get_page(int(page_number or 1))

        serialized_list = self.read_serializer_class(queryset, many=True, context={"request": request})
        data = add_count(serialized_list.data, count)

        return SuccessResponse(data=data, message="Fetched successfully", status=status.HTTP_200_OK)


class MaintenanceDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    # Using these parser classes because of the
    # image field when updating the Maintenance object
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = MaintenanceUpdateSerializer
    read_serializer_class = MaintenanceReadSerializer

    @extend_schema(
        operation_id="maintenance_detail",
        request=serializer_class,
        responses={
            202: OpenApiResponse(
                response=serializer_class,
                description="Fetched successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Maintenance"],
        description="Fetch maintenance detail",
    )
    @client_or_technician_required
    def get(self, request, uuid):
        """
        Retrieve a model instance.
        """
        instance = get_object_or_404(Maintenance, uuid=uuid, is_deleted=False)
        serializer = self.read_serializer_class(instance)
        return SuccessResponse(
            data=serializer.data,
            message="Fetched successfully",
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="update_maintenance",
        request=serializer_class,
        responses={
            202: OpenApiResponse(
                response=serializer_class,
                description="Updated successfully",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Maintenance"],
        description="Update Maintenance",
    )
    @client_required()
    def patch(self, request, uuid):
        instance = get_object_or_404(Maintenance, uuid=uuid, is_deleted=False)
        serializer = self.serializer_class(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(
            data=serializer.data,
            message="Data updated successfully",
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(
        operation_id="delete_maintenance",
        responses={
            204: OpenApiResponse(
                description="Deleted successfully",
            ),
            404: ErrorResponseSerializer,
        },
        tags=["Maintenance"],
        description="Delete a Maintenance by uuid",
    )
    @client_required()
    def delete(self, request, uuid):
        instance = get_object_or_404(Maintenance, uuid=uuid, is_deleted=False)
        instance.is_deleted = True
        instance.save()
        return SuccessResponse(status=status.HTTP_204_NO_CONTENT)
