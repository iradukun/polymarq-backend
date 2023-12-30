from django.conf import settings
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import decorators, get_user_model

from polymarq_backend.apps.users import models
from polymarq_backend.apps.users.forms import UserAdminChangeForm, UserAdminCreationForm

# from django.utils.translation import gettext_lazy as _


User = get_user_model()

if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow:
    # https://django-allauth.readthedocs.io/en/stable/advanced.html#admin
    admin.site.login = decorators.login_required(admin.site.login)  # type: ignore[method-assign]


@admin.register(User)
class CustomUserAdmin(auth_admin.UserAdmin):
    list_display = (
        "username",
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "is_staff",
        "is_active",
        "uuid",
    )
    ordering = ["-date_joined"]
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    search_fields = ["email", "first_name", "last_name"]
    fieldsets = auth_admin.UserAdmin.fieldsets + (
        (
            "Other Information",
            {
                "fields": (
                    "phone_number",
                    "is_verified",
                    "is_client",
                    "profile_picture",
                    "is_technician",
                    "longitude",
                    "latitude",
                )
            },
        ),  # type: ignore
        # (
        #     _("Permissions"),
        #     {
        #         "fields": (
        #             "is_active",
        #             "is_superuser",
        #             "groups",
        #             "user_permissions",
        #         ),
        #     },
        # ),
        # (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )


@admin.register(models.VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "phone_number",
        "code",
        "used",
    )
    readonly_fields = ("code", "created_at")


@admin.register(models.Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "account_type",
    )
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(models.Technician)
class TechnicianAdmin(admin.ModelAdmin):
    list_display = ("user",)
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(models.TechnicianCertificate)
class TechnicianCertificateAdmin(admin.ModelAdmin):
    list_display = ("technician", "file")
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.TechnicianType)
class TechnicianTypeAdmin(admin.ModelAdmin):
    list_display = ("title",)
    readonly_fields = ("created_at", "updated_at")
