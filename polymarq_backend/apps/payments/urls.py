from django.urls import path

from polymarq_backend.apps.payments.views import (
    BanksListView,
    ClientJobStateView,
    CreateTechnicianBankAccountInformationView,
    JobIncrementalPaymentListView,
    PaystackTransactionsWebhook,
    TechnicianJobStateView,
)

app_name = "payments"

urlpatterns = [
    path(
        "job-states/technicians/<uuid:job_uuid>/",
        TechnicianJobStateView.as_view(),  # type: ignore
        name="update-technician-job-state",  # noqa: E501 # type: ignore
    ),
    path(
        "job-states/clients/<uuid:job_uuid>/",
        ClientJobStateView.as_view(),  # type: ignore
        name="update-client-job-state",
    ),  # noqa: E501 # type: ignore
    path(
        "jobs/<uuid:job_uuid>/",
        JobIncrementalPaymentListView.as_view(),  # type: ignore
        name="incremental-payments-list",
    ),  # type: ignore
    path(
        "technician-bank-accounts/create/",
        CreateTechnicianBankAccountInformationView.as_view(),  # type: ignore
        name="create-technician-bank-account-information",
    ),  # type: ignore
    path(
        "paystack/webhook/",
        PaystackTransactionsWebhook.as_view(),  # type: ignore
        name="paystack-webhook",
    ),  # type: ignore
    path("banks/list/", BanksListView.as_view(), name="banks-list"),
]
