from django.urls import path

from polymarq_backend.apps.users.api.clients.views import AuthorizedClientDetailView, ClientDetailView, ClientListView
from polymarq_backend.apps.users.api.technicians.views import (
    AuthorizedTechnicianDetailView,
    TechnicianDetailView,
    TechnicianListView,
    TechniciansNearbyView,
    TechnicianTypeDetail,
    TechnicianTypeView,
)
from polymarq_backend.apps.users.api.views import UserUpdateProfilePictureView

# if settings.DEBUG:
#     router = DefaultRouter()
# else:
#     router = SimpleRouter()

# router.register("users", UserViewSet)

_patterns = [
    path("user/profile-picture/", UserUpdateProfilePictureView.as_view(), name="user-profile-picture"),  # type: ignore # noqa: E501]
    path("technicians/", TechnicianListView.as_view(), name="technician-profiles-list"),  # type: ignore # noqa: E501]
    path("technicians/<uuid:uuid>/", TechnicianDetailView.as_view(), name="technician-user-profile"),  # type: ignore # noqa: E501
    path("technicians/profile/", AuthorizedTechnicianDetailView.as_view(), name="authorized-technician-user-profile"),  # type: ignore # noqa: E501
    path("technicians/nearby/", TechniciansNearbyView.as_view(), name="technicians-nearby"),  # type: ignore # noqa: E501
    path("clients/", ClientListView.as_view(), name="client-profiles-list"),  # type: ignore # noqa: E501
    path("clients/<uuid:uuid>/", ClientDetailView.as_view(), name="client-user-profile"),  # type: ignore # noqa: E501
    path("clients/profile/", AuthorizedClientDetailView.as_view(), name="authorized-client-user-profile"),  # type: ignore # noqa: E501
    path("technician-types/", TechnicianTypeView.as_view(), name="technician-types"),  # type: ignore # noqa: E501
    path("technician-types/<uuid:uuid>/", TechnicianTypeDetail.as_view(), name="technician-types-detail"),  # type: ignore # noqa: E501
]

app_name = "api"
# urlpatterns = router.urls + _patterns
urlpatterns = _patterns
