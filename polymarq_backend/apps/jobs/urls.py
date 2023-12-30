from django.urls import path

from polymarq_backend.apps.jobs.views import (
    CreateJobView,
    CreatePingView,
    JobDetailView,
    JobInitialPaymentInitiateView,
    JobRequests,
    ListJobView,
    TechnicianSearchView,
    UpdatePingView,
)

app_name = "jobs"
urlpatterns = [
    path("", ListJobView.as_view(), name="list-jobs"),  # type: ignore
    path("create/", CreateJobView.as_view(), name="create-job"),  # type: ignore
    path("<uuid:uuid>/", JobDetailView.as_view(), name="get-patch-delete-job"),  # type: ignore
    path("technician-search/", TechnicianSearchView.as_view(), name="technician-search"),  # type: ignore
    path("requests/", JobRequests.as_view(), name="job-requests"),  # type: ignore
    path("ping/create/", CreatePingView.as_view(), name="create-ping"),  # type: ignore
    path("ping/accept-or-decline/<str:uuid>/", UpdatePingView.as_view(), name="accept-or-decline-ping"),  # type: ignore # noqa: E501
    path("payment/initiate/", JobInitialPaymentInitiateView.as_view(), name="initiate-payment"),  # type: ignore
]
