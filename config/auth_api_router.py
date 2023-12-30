from django.urls import path

# from rest_framework.routers import DefaultRouter, SimpleRouter
from rest_framework_simplejwt.views import TokenRefreshView

from polymarq_backend.apps.users.api.clients.views import ClientRegistrationPhoneView, ClientRegistrationView
from polymarq_backend.apps.users.api.technicians.views import (
    TechnicianRegistrationPhoneView,
    TechnicianRegistrationView,
)
from polymarq_backend.apps.users.api.views import (
    ConfirmPhoneVerification,
    CustomResetPasswordConfirm,
    CustomResetPasswordRequestToken,
    CustomResetPasswordValidateToken,
    InitiatePhoneVerification,
    ResendVerificationCode,
    UserLoginView,
    UserLogoutView,
    UserPhoneResetPasswordRequestTokenView,
    VerifyUserAccount,
)

# if settings.DEBUG:
#     router = DefaultRouter()
# else:
#     router = SimpleRouter()

# router.register("users", UserViewSet)


_patterns = [
    path("register/client/", ClientRegistrationView.as_view(), name="client-user-register"),  # type: ignore # noqa: E501
    path("register/client/phone/", ClientRegistrationPhoneView.as_view(), name="client-user-phone-register"),  # type: ignore # noqa: E501
    path("register/technician/", TechnicianRegistrationView.as_view(), name="technician-user-register"),  # type: ignore # noqa: E501
    path("register/technician/phone", TechnicianRegistrationPhoneView.as_view(), name="technician-user-phone-register"),  # type: ignore # noqa: E501
    path("verify/", VerifyUserAccount.as_view(), name="user-verification"),  # type: ignore
    path("phone-verification/initiate/", InitiatePhoneVerification.as_view(), name="user-phone-verification"),  # type: ignore # noqa: E501
    path("phone-verification/verify/", ConfirmPhoneVerification.as_view(), name="user-phone-confirm"),  # type: ignore
    path("resend-verification/", ResendVerificationCode.as_view(), name="user-verification-resend"),  # type: ignore # noqa: E501
    path("login/", UserLoginView.as_view(), name="user-login"),  # type: ignore
    path("logout/", UserLogoutView.as_view(), name="user-logout"),  # type: ignore
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),  # type: ignore
    path("password-reset/", CustomResetPasswordRequestToken.as_view(), name="reset-password-request"),  # type: ignore # noqa: E501
    path("password-reset/confirm/", CustomResetPasswordConfirm.as_view(), name="reset-password-confirm"),  # type: ignore # noqa: E501
    path("password-reset/validate-token/", CustomResetPasswordValidateToken.as_view(), name="reset-password-validate"),  # type: ignore # noqa: E501
    path("phone/password-reset/", UserPhoneResetPasswordRequestTokenView.as_view(), name="phone-reset-password-request"),  # type: ignore # noqa: E501
    # just for uniformity sake, there's no need for the endpoints below,
    # but they are here for consistency for phone number reset password
    # else we could have easily reused the endpoints above
    path("phone/password-reset/validate-token/", CustomResetPasswordValidateToken.as_view(), name="phone-reset-password-validate"),  # type: ignore # noqa: E501
    path("phone/password-reset/confirm/", CustomResetPasswordConfirm.as_view(), name="phone-reset-password-confirm"),  # type: ignore # noqa: E501
]

app_name = "auth-api"
# urlpatterns = router.urls + _patterns
urlpatterns = _patterns
