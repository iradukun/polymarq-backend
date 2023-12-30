from django.urls import path

from polymarq_backend.apps.tools.views import (
    CreateToolView,
    ToolCategoryView,
    ToolNegotiationResponseView,
    ToolNegotiationView,
    ToolPurchaseInitiateView,
    ToolRentalDetailView,
    ToolRentalRequestAcceptView,
    ToolRentalRequestDeclineView,
    ToolRentalRequestListView,
    ToolRentalRequestView,
    ToolsCountsView,
    ToolsDetailView,
    ToolsListView,
)

app_name = "tools"
urlpatterns = [
    path("", ToolsListView.as_view(), name="list-tools"),  # type: ignore
    path("counts/", ToolsCountsView.as_view(), name="list-tools-counts"),  # type: ignore
    path("create/", CreateToolView.as_view(), name="create-tools"),  # type: ignore
    path("categories/", ToolCategoryView.as_view(), name="tool-categories"),  # type: ignore
    path("rent-requests/", ToolRentalRequestView.as_view(), name="tool-rent-request"),  # type: ignore
    path("<uuid:uuid>/", ToolsDetailView.as_view(), name="tool-detail"),  # type: ignore
    path(
        "<uuid:uuid>/rent-requests/",
        ToolRentalRequestListView.as_view(),  # type: ignore
        name="tool-rent-request-list",
    ),
    path("rent-requests/accept/<uuid:uuid>/", ToolRentalRequestAcceptView.as_view(), name="accept-rent-request"),  # type: ignore # noqa: E501
    path(
        "rent-requests/decline/<uuid:uuid>/",
        ToolRentalRequestDeclineView.as_view(),  # type: ignore
        name="decline-rent-request",
    ),
    path("rent-requests/<uuid:uuid>/", ToolRentalDetailView.as_view(), name="rent-request-detail"),  # type: ignore
    path("negotiate/", ToolNegotiationView.as_view(), name="negotiate-tool"),  # type: ignore
    path("negotiate/response/", ToolNegotiationResponseView.as_view(), name="negotiate-tool-response"),  # type: ignore
    path("purchase/initiate", ToolPurchaseInitiateView.as_view(), name="purchase-initiate"),  # type: ignore
]  # Mind the positions of the above routes
