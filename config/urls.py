from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

# set/define api version as v1
API_VERSION = "v1"

urlpatterns = [
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path("about/", TemplateView.as_view(template_name="pages/about.html"), name="about"),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("polymarq_backend.apps.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_title = "Polymarq Backend Admin"
admin.site.site_header = "Polymarq Backend Admin"
admin.site.index_title = "Polymarq Backend Admin"

# update all api routes to include api version
# API URLS
API_PATH_PREFIX = f"api/{API_VERSION}/"
urlpatterns += [
    # API base url
    path(f"{API_PATH_PREFIX}auth/", include("config.auth_api_router")),
    path(f"{API_PATH_PREFIX}", include("config.api_router")),
    path(
        f"{API_PATH_PREFIX}job/",
        include("polymarq_backend.apps.jobs.urls", namespace="jobs_app"),
    ),
    path(
        f"{API_PATH_PREFIX}maintenance/",
        include("polymarq_backend.apps.maintenance.urls", namespace="maintenance_app"),
    ),
    path(
        f"{API_PATH_PREFIX}tools/",
        include("polymarq_backend.apps.tools.urls", namespace="tools_app"),
    ),
    path(
        f"{API_PATH_PREFIX}payments/",
        include("polymarq_backend.apps.payments.urls", namespace="payments_app"),
    ),
    path(
        f"{API_PATH_PREFIX}notifications/",
        include("polymarq_backend.apps.notifications.urls", namespace="notifications_app"),
    ),
    # DRF auth token
    # path("auth-token/", obtain_auth_token),
    path(f"{API_PATH_PREFIX}schema/", SpectacularAPIView.as_view(), name="api-schema"),  # type: ignore
    path(
        f"{API_PATH_PREFIX}docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),  # type: ignore
        name="api-docs",
    ),
]

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar  # type: ignore

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
