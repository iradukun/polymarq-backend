from django.urls import path

from polymarq_backend.apps.maintenance.views import CreateMaintenanceView, ListMaintenanceView, MaintenanceDetailView

app_name = "maintenance"
urlpatterns = [
    path("", ListMaintenanceView.as_view(), name="list-maintenance"),
    path("create/", CreateMaintenanceView.as_view(), name="create-maintenance"),  # type: ignore
    path("<uuid:uuid>/", MaintenanceDetailView.as_view(), name="get-patch-delete-maintenance"),
]
