from django.urls import path

from polymarq_backend.apps.notifications.views import NotificationDetailView, NotificationListView

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("<uuid:uuid>/", NotificationDetailView.as_view(), name="notification-detail"),
]
