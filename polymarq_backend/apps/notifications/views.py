from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema  # type: ignore
from rest_framework import status
from rest_framework.views import APIView

from polymarq_backend.apps.notifications.models import Notification
from polymarq_backend.apps.notifications.serializers import (
    NotificationCountSerializer,
    NotificationReadSerializer,
    NotificationSerializer,
    NotificationUpdateSerializer,
)
from polymarq_backend.apps.users.api.serializers import ErrorResponseSerializer
from polymarq_backend.core.success_response import SuccessResponse
from polymarq_backend.core.utils.main import add_count


class NotificationListView(APIView):
    serializer_class = NotificationReadSerializer

    @extend_schema(
        operation_id="notification_list",
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Specify the page of the fetched list (`all` can be set to fetch all)",
                required=False,
                default=1,
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Specify the limit for each page fetched",
                required=False,
                default=settings.DEFAULT_PAGE_SIZE,
            ),
            OpenApiParameter(
                name="order",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Sort fetched list",
                required=False,
                default="asc",
                enum=["asc", "desc"],
            ),
            OpenApiParameter(
                name="unread",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Fetch only unread notifications",
                required=False,
                default=False,
            ),
        ],  # type: ignore
        responses={
            200: OpenApiResponse(
                response=NotificationCountSerializer,
                description="Resource fetched successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Notifications"],
        description="Fetch Notifications",
    )
    def get(self, request):
        order = request.GET.get("order", "desc")  # sorting order
        page = request.GET.get("page", 1)  # page number
        limit = request.GET.get("limit", settings.DEFAULT_PAGE_SIZE)  # limit per page
        unread = request.GET.get("unread")
        queries = Q(is_deleted=False)

        if unread == "true":
            queries &= Q(is_read=False)

        notifications = Notification.objects.filter(queries, recipient=request.user).order_by(
            "-created_at" if order == "desc" else "created_at"
        )

        unread_count, total_count = (
            notifications.filter(is_read=False).count(),
            notifications.count(),
        )

        if limit != "all":
            paginator = Paginator(notifications, int(limit))
            notifications = paginator.get_page(int(page))

        serializer = NotificationReadSerializer(notifications, many=True)
        data = add_count(
            serializer.data,
            total_count,
            unread_count=unread_count,
        )
        return SuccessResponse(data=data, message="Notifications fetched succesfully.")  # type: ignore


class NotificationDetailView(APIView):
    serializer_class = NotificationSerializer
    update_serializer_class = NotificationUpdateSerializer

    @extend_schema(
        operation_id="notification_update",
        request=update_serializer_class,
        responses={
            202: OpenApiResponse(
                description="Notification updated successfully.",
            ),
            400: ErrorResponseSerializer,
        },
        tags=["Notifications"],
        description="Update a notification by uuid",
    )
    def patch(self, request, uuid):
        notification = get_object_or_404(Notification, uuid=uuid, is_deleted=False)
        serializer = self.update_serializer_class(notification, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(
            status=status.HTTP_202_ACCEPTED,
            message="Notification updated successfully.",
        )

    @extend_schema(
        operation_id="notification_delete",
        responses={
            204: OpenApiResponse(
                description="Deleted successfully",
            ),
            404: ErrorResponseSerializer,
        },
        tags=["Notifications"],
        description="Delete a notification by uuid",
    )
    def delete(self, request, uuid):
        notification = get_object_or_404(Notification, uuid=uuid, is_deleted=False)
        notification.is_deleted = True
        notification.save()
        return SuccessResponse(
            status=status.HTTP_204_NO_CONTENT,
            message="Notification deleted successfully.",
        )
