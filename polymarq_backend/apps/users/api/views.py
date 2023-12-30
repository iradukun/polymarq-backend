import json
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.models import ResetPasswordToken, clear_expired, get_password_reset_token_expiry_time
from django_rest_passwordreset.serializers import EmailSerializer
from django_rest_passwordreset.views import (
    ResetPasswordConfirm,
    ResetPasswordRequestToken,
    ResetPasswordValidateToken,
    ResetTokenSerializer,
)
from djangorestframework_camel_case.parser import CamelCaseJSONParser
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from polymarq_backend.apps.aws_sns.models import Device
from polymarq_backend.apps.aws_sns.tasks import deregister_device, register_device
from polymarq_backend.apps.users.models import VerificationCode
from polymarq_backend.apps.users.signals import phone_reset_password_token_created
from polymarq_backend.apps.users.utils import get_tokens_for_user
from polymarq_backend.core.error_response import ErrorResponse
from polymarq_backend.core.sender import Sender
from polymarq_backend.core.success_response import SuccessResponse
from polymarq_backend.core.utils.dict_to_object import DictToObject
from polymarq_backend.core.utils.main import unicode_ci_compare

from ..utils import get_custom_user_model
from .serializers import (
    CustomPasswordTokenSerializer,
    ErrorResponseSerializer,
    SuccessResponseSerializer,
    UserLoginSerializer,
    UserLogoutSerializer,
    UserPhoneNumberSerializer,
    UserSerializer,
    UserUpdateProfilePictureSerializer,
    VerifyUserPhoneNumberSerializer,
    VerifyUserSerializer,
)

User = get_custom_user_model()

HTTP_USER_AGENT_HEADER = getattr(settings, "DJANGO_REST_PASSWORDRESET_HTTP_USER_AGENT_HEADER", "HTTP_USER_AGENT")
HTTP_IP_ADDRESS_HEADER = getattr(settings, "DJANGO_REST_PASSWORDRESET_IP_ADDRESS_HEADER", "REMOTE_ADDR")
APPLICATION_ENVIRONMENT = getattr(settings, "APPLICATION_ENVIRONMENT", "local")


class UserViewSet(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    parser_classes = [CamelCaseJSONParser]
    lookup_field = "username"

    def get_queryset(self, *args, **kwargs):
        assert isinstance(self.request.user.id, int)  # type: ignore # sanity check
        return self.queryset.filter(id=self.request.user.id)  # type: ignore

    @action(detail=False)
    def me(self, request):
        serializer = UserSerializer(request.user, context={"request": request})
        return SuccessResponse(data=serializer.data, status=status.HTTP_200_OK)


class UserUpdateProfilePictureView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = UserUpdateProfilePictureSerializer

    @extend_schema(
        request=serializer_class,
        responses={200: SuccessResponseSerializer, 400: ErrorResponseSerializer},
        tags=["Users"],
        description="Update a user's profile picture",
    )
    def post(self, request):
        serializer = self.serializer_class(request.user, data=request.data, context={"request": request}, partial=True)

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return SuccessResponse(
            data=serializer.data,
            message="Profile picture updated successfully",
            status=status.HTTP_200_OK,
        )


class VerifyUserAccount(APIView):
    permission_classes = [AllowAny]
    serializer_class = VerifyUserSerializer

    @extend_schema(
        request=serializer_class,
        responses={200: SuccessResponseSerializer, 400: ErrorResponseSerializer},
        tags=["Auth"],
        description="Verify a user account",
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request": request})

        if not serializer.is_valid():
            return ErrorResponse(details=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]  # type: ignore
        code = serializer.validated_data["code"]  # type: ignore

        if len(code) != 6:
            return ErrorResponse(details="Invalid code format", status=status.HTTP_400_BAD_REQUEST)

        try:
            verification_code = VerificationCode.objects.get(code=code, user__email=email)
        except VerificationCode.DoesNotExist:
            return ErrorResponse(details="Code not found", status=status.HTTP_404_NOT_FOUND)

        if verification_code.used:
            return ErrorResponse(details="Code already used", status=status.HTTP_400_BAD_REQUEST)

        verification_code.used = True
        verification_code.user.is_verified = True  # type: ignore
        verification_code.user.save(update_fields=["is_verified"])  # type: ignore
        verification_code.save(update_fields=["used"])

        return SuccessResponse(message="User account verified", status=status.HTTP_200_OK)


class ResendVerificationCode(APIView):
    permission_classes = [AllowAny]
    serializer_class = EmailSerializer

    @extend_schema(
        request=serializer_class,
        responses={200: SuccessResponseSerializer, 400: ErrorResponseSerializer},
        tags=["Auth"],
        description="Resend a verification code to a user",
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request": request})

        if not serializer.is_valid():
            return ErrorResponse(details=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]  # type: ignore

        try:
            user = User.user_manager.get(email=email)
        except User.DoesNotExist:
            return ErrorResponse(
                details="User with email does not exist",
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.is_verified:
            return ErrorResponse(
                details="User account already verified",
                status=status.HTTP_400_BAD_REQUEST,
            )

        verification_code = VerificationCode.objects.create(user=user)

        context = {"user": user, "verification_code": verification_code.code}

        Sender(
            user,
            email_content_object="notification.messages.user_registration",
            html_template="emails/authentication/user-verification.html",
            email_notif=True,
            context=context,
        )

        return SuccessResponse(message="Verification code sent successfully", status=status.HTTP_200_OK)


class InitiatePhoneVerification(APIView):
    permission_classes = [AllowAny]
    serializer_class = UserPhoneNumberSerializer

    @extend_schema(
        request=serializer_class,
        responses={200: SuccessResponseSerializer, 400: ErrorResponseSerializer},
        tags=["Auth"],
        description="Verify a user phone number via sms for users who wants to create an account using phone number",
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            return ErrorResponse(details=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number = serializer.validated_data["phone_number"]  # type: ignore

        verification_code = VerificationCode.objects.create(phone_number=phone_number)

        # context = {"user": user, "verification_code": verification_code.code}
        user = DictToObject({"phone_number": phone_number})
        Sender(
            user,
            sms_notif=True,
            sms_message=f"Your Polymarq verification code is {verification_code.code}",
        )

        return SuccessResponse(message="Verification code sent successfully", status=status.HTTP_200_OK)


class ConfirmPhoneVerification(APIView):
    permission_classes = [AllowAny]
    serializer_class = VerifyUserPhoneNumberSerializer

    @extend_schema(
        request=serializer_class,
        responses={200: SuccessResponseSerializer, 400: ErrorResponseSerializer},
        tags=["Auth"],
        description="Verify a user phone number using code sent to phone number",
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request": request})

        if not serializer.is_valid():
            return ErrorResponse(details=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number = serializer.validated_data["phone_number"]  # type: ignore
        code = serializer.validated_data["code"]  # type: ignore

        if len(code) != 6:
            return ErrorResponse(details="Invalid code format", status=status.HTTP_400_BAD_REQUEST)

        try:
            verification_code = VerificationCode.objects.get(code=code, phone_number=phone_number)
        except VerificationCode.DoesNotExist:
            return ErrorResponse(details="Code not found", status=status.HTTP_404_NOT_FOUND)

        if verification_code.used:
            return ErrorResponse(details="Code already used", status=status.HTTP_400_BAD_REQUEST)

        verification_code.used = True
        verification_code.save(update_fields=["used"])

        return SuccessResponse(message="Phone number verified", status=status.HTTP_200_OK)


class UserPhoneResetPasswordRequestTokenView(APIView):
    """
    An Api View which provides a method to request a password reset token based on an e-mail address

    Sends a signal reset_password_token_created when a reset token was created
    """

    throttle_classes = ()
    permission_classes = ()
    serializer_class = UserPhoneNumberSerializer
    authentication_classes = ()

    @extend_schema(
        request=serializer_class,
        responses={200: SuccessResponseSerializer, 400: ErrorResponseSerializer},
        tags=["Auth"],
        description="Allows a user to request a password reset token based on a phone number. \
        Sends a signal reset_password_token_created when a reset token was created",
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse(details=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        phone_number = serializer.validated_data["phone_number"]  # type: ignore

        # before we continue, delete all existing expired tokens
        password_reset_token_validation_time = get_password_reset_token_expiry_time()

        # datetime.now minus expiry hours
        now_minus_expiry_time = timezone.now() - timedelta(hours=password_reset_token_validation_time)

        # delete all tokens where created_at < now - 24 hours
        clear_expired(now_minus_expiry_time)

        # find a user by phone number (case insensitive search)
        users = User.user_manager.filter(username__iexact=phone_number)

        active_user_found = False

        # iterate over all users and check if there is any user that is active
        # also check whether the password can be changed (is useable), as there could be users that are not allowed
        # to change their password (e.g., LDAP user)
        for user in users:
            if user.eligible_for_reset():  # type: ignore
                active_user_found = True
                break

        # No active user found, raise a validation error
        # but not if DJANGO_REST_PASSWORDRESET_NO_INFORMATION_LEAKAGE == True
        if not active_user_found and not getattr(settings, "DJANGO_REST_PASSWORDRESET_NO_INFORMATION_LEAKAGE", False):
            raise ValidationError(
                {
                    "phone_number": [
                        _(
                            "We couldn't find an account associated with that phone_number. \
                            Please try a different phone_number address."
                        )
                    ],
                }
            )

        # last but not least: iterate over all users that are active and can change their password
        # and create a Reset Password Token and send a signal with the created token
        for user in users:
            if user.eligible_for_reset() and unicode_ci_compare(  # type: ignore
                phone_number, getattr(user, "phone_number")
            ):
                # define the token as none for now
                token = None

                # check if the user already has a token
                if user.password_reset_tokens.all().count() > 0:  # type: ignore
                    # yes, already has a token, re-use this token
                    token = user.password_reset_tokens.all()[0]  # type: ignore
                else:
                    # no token exists, generate a new token
                    token = ResetPasswordToken.objects.create(
                        user=user,
                        user_agent=request.META.get(HTTP_USER_AGENT_HEADER, ""),
                        ip_address=request.META.get(HTTP_IP_ADDRESS_HEADER, ""),
                    )
                # send a signal that the password token was created
                # let whoever receives this signal handle sending the email for the password reset
                phone_reset_password_token_created.send(
                    sender=self.__class__, instance=self, reset_password_token=token
                )
        # done
        return SuccessResponse(message="Password reset code sent", status=status.HTTP_201_CREATED)


class UserLoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = UserLoginSerializer

    @extend_schema(
        request=serializer_class,
        responses={200: SuccessResponseSerializer, 400: ErrorResponseSerializer},
        tags=["Auth"],
        description="Login a user" + "\nNB: For the 'device_type' field, '0' is IOS and '1' is Android.",
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request": request})

        if not serializer.is_valid():
            return ErrorResponse(details=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.validated_data.get("username")  # type: ignore
        password = serializer.validated_data.get("password")  # type: ignore

        if not username or not password:
            return ErrorResponse(
                details="Username and password are required",
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.user_manager.get(username=username)
        except User.DoesNotExist:
            return ErrorResponse(
                details="User with username does not exist",
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.check_password(password):  # type: ignore
            return ErrorResponse(
                details="Invalid password",
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.is_verified:
            return ErrorResponse(details="User account not verified", status=status.HTTP_400_BAD_REQUEST)

        if APPLICATION_ENVIRONMENT != "local":
            # Register user's device on AWS SNS
            device_token = serializer.validated_data.get("device_token")  # type: ignore
            device_type = serializer.validated_data.get("device_type")  # type: ignore

            devices = Device.objects.filter(token=device_token)
            if devices.count() == 0:
                # Register new device
                device = Device()
                device.user = user
                device.token = device_token  # type: ignore
                device.os = device_type  # type: ignore
                device.save()
                register_device(device)
            else:
                # check for previously registered devices
                device = devices.first()
                if device.active is False:  # type: ignore
                    # Re-register if previously registered
                    device.user = user  # type: ignore
                    device.os = device_type  # type: ignore
                    device.active = True  # type: ignore
                    device.save()  # type: ignore
                    register_device(device)
                else:
                    # Do nothing if active user
                    pass

        tokens = get_tokens_for_user(user)
        # include user object in response data
        user_data = UserSerializer(user).data
        response_data = {
            "user": user_data,
            "tokens": {**tokens},
        }

        return SuccessResponse(data=response_data, message="Login successful", status=status.HTTP_200_OK)


class UserLogoutView(APIView):
    """
    Logs out the user by invalidating their tokens.
    """

    @extend_schema(
        request=UserLogoutSerializer,
        responses={200: SuccessResponseSerializer, 400: ErrorResponseSerializer},
        tags=["Auth"],
        description="Logouts a user account. Expects a refresh token, device_type and device_token."
        + "\nNB: For the 'device_type' field, '0' is IOS and '1' is Android.",
    )
    def post(self, request):
        refresh_token = request.data.get("refresh")
        device_token = request.data.get("device_token")
        device_type = request.data.get("device_type")

        if not refresh_token:
            return ErrorResponse(
                details="Refresh token is required",
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()  # Invalidate the refresh token

            # unregister device to stop sending push notifications
            # to the device
            device = Device.objects.filter(token=device_token, os=device_type)
            if device.count() == 0:
                return ErrorResponse(
                    details="Device Not Found",
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                # Get device object from the queryset
                device = device.first()
                deregister_device(device)

            return SuccessResponse(
                message="User successfully logged out",
                status=status.HTTP_205_RESET_CONTENT,
            )

        except Exception as e:  # noqa
            return ErrorResponse(
                details="Invalid refresh token",
                status=status.HTTP_400_BAD_REQUEST,
            )


class CustomResetPasswordRequestToken(APIView):
    serializer_class = EmailSerializer
    permission_classes = ()
    authentication_classes = ()

    @extend_schema(
        request=EmailSerializer,
        responses={200: SuccessResponseSerializer, 400: ErrorResponseSerializer},
        tags=["Auth"],
        description="""An Api View which provides a method to request a password
        reset token based on an e-mail address. Sends a signal reset_password_token_created
        when a reset token was created""",
    )
    def post(self, request, *args, **kwargs):
        # Call the existing view
        reset_view = ResetPasswordRequestToken.as_view()
        response = reset_view(request=request._request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            return SuccessResponse(
                message="Password request token sent successfully",
                status=response.status_code,
                data=response.data,  # type: ignore
            )
        else:
            error_data = response.data.get("error", [])  # type: ignore
            if error_data:
                details = str(error_data[0].get("details"))
            else:
                details = "Check the request payload and try again"
            return ErrorResponse(
                message="Request for password reset token failed",
                details=details,
                status=response.status_code,
            )


class CustomResetPasswordConfirm(APIView):
    throttle_classes = ()
    permission_classes = ()
    serializer_class = CustomPasswordTokenSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CustomPasswordTokenSerializer,
        responses={200: SuccessResponseSerializer, 400: ErrorResponseSerializer},
        tags=["Auth"],
        description="An Api View which provides a method to reset a password based on a unique token.",
    )
    def post(self, request, *args, **kwargs):
        try:
            json_data = json.loads(request._request.body)  # getting the request body raw
        except json.decoder.JSONDecodeError:
            return ErrorResponse(status=status.HTTP_400_BAD_REQUEST, message="Invalid JSON body")

        # Validate current password only if set
        if json_data.get("old_password") and not request.user.check_password(json_data.get("old_password")):
            return ErrorResponse(status=status.HTTP_403_FORBIDDEN, message="Invalid password")

        # Call the existing view
        reset_password_confirm_view = ResetPasswordConfirm.as_view()
        response = reset_password_confirm_view(request=request._request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            return SuccessResponse(
                message="Password reset successfully",
                status=response.status_code,
                data=response.data,  # type: ignore
            )
        else:
            error_data = response.data.get("error", [])  # type: ignore
            if len(error_data) > 0:
                details = error_data
            else:
                details = "Check the request payload and try again"

            return ErrorResponse(
                message="Password reset failed",
                details=details,
                status=response.status_code,
            )


class CustomResetPasswordValidateToken(APIView):
    throttle_classes = ()
    permission_classes = ()
    serializer_class = ResetTokenSerializer
    authentication_classes = ()

    @extend_schema(
        request=ResetTokenSerializer,
        responses={200: SuccessResponseSerializer, 400: ErrorResponseSerializer},
        tags=["Auth"],
        description="An Api View which provides a method to verify that a token is valid.",
    )
    def post(self, request, *args, **kwargs):
        # Call the existing view
        reset_password_validate_token_view = ResetPasswordValidateToken.as_view()
        response = reset_password_validate_token_view(request=request._request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            return SuccessResponse(
                message="Password reset token validated successfully",
                status=response.status_code,
                data=response.data,  # type: ignore
            )
        else:
            error_data = response.data.get("error", [])  # type: ignore
            if error_data:
                details = str(error_data[0].get("details"))
            else:
                details = "Check the request payload and try again"
            return ErrorResponse(
                message="Password reset token validation failed",
                details=details,
                status=response.status_code,
            )
