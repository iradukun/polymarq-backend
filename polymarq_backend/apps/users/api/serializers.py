import json
from typing import Any, cast

from django.conf import settings
from django.contrib.auth.password_validation import get_password_validators, validate_password
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.serializers import PasswordTokenSerializer
from rest_framework import serializers

from polymarq_backend.apps.aws_sns.models import Device
from polymarq_backend.apps.users.models import Client, Technician, TechnicianCertificate, TechnicianType
from polymarq_backend.apps.users.types import UserType

# from django.contrib.auth import get_user_model
from polymarq_backend.apps.users.utils import get_custom_user_model
from polymarq_backend.core.success_response import SuccessResponseSerializer
from polymarq_backend.core.utils.main import normalize_phone_number

User = get_custom_user_model()


class UserFullNameField(serializers.CharField):
    def to_internal_value(self, data):
        # Split the incoming full name into first name and last name
        if type(data) is str:
            names = data.split()
            if len(names) > 1:
                return {
                    "first_name": names[0],
                    "last_name": " ".join(names[1:]),
                }
            else:
                return {
                    "first_name": names[0],
                    "last_name": "",
                }
        return data

    def to_representation(self, obj):
        # Combine first name and last name into full name during serialization
        return f"{obj['first_name']} {obj['last_name']}"


class PasswordField(serializers.CharField):
    def to_internal_value(self, data):
        # Validate the password using Django's validators
        validate_password(
            data,
            password_validators=get_password_validators(settings.AUTH_PASSWORD_VALIDATORS),
        )
        return data


class UserSerializer(serializers.ModelSerializer[UserType]):
    class Meta:
        model = User
        exclude = (
            "password",
            "is_staff",
            "is_active",
            "date_joined",
            "is_superuser",
            "groups",
            "user_permissions",
            "last_login",
            "is_technician",
            "is_client",
            "is_verified",
            "id",
        )

        # extra_kwargs = {
        #     "url": {"view_name": "users:detail", "lookup_field": "username"},
        # }


class UserReadSerializer(serializers.ModelSerializer[UserType]):
    class Meta:
        model = User
        exclude = (
            "uuid",
            "email",
            "phone_number",
            "password",
            "is_staff",
            "is_active",
            "date_joined",
            "is_superuser",
            "groups",
            "user_permissions",
            "last_login",
            "is_technician",
            "is_client",
            "is_verified",
            "id",
        )

        # extra_kwargs = {
        #     "url": {"view_name": "users:detail", "lookup_field": "username"},
        # }


class UserCreateSerializer(serializers.ModelSerializer[UserType]):
    password = PasswordField(write_only=True)
    full_name = UserFullNameField(write_only=True, required=False)

    class Meta:
        model = User
        fields = (
            "email",
            "password",
            "phone_number",
            "full_name",
            "username",
            "longitude",
            "latitude",
        )

        extra_kwargs = {
            "username": {"required": False},
        }

    def create(self, validated_data):
        # Handle full_name field and convert it to first_name and last_name
        full_name = validated_data.pop("full_name", None)
        if full_name:
            validated_data["first_name"] = full_name.get("first_name", "")
            validated_data["last_name"] = full_name.get("last_name", "")

        user = User.user_manager.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            username=validated_data.get("username", None),
            phone_number=validated_data.get("phone_number", ""),
            longitude=validated_data.get("longitude", None),
            latitude=validated_data.get("latitude", None),
            is_client=validated_data.get("is_client", False),
            is_technician=validated_data.get("is_technician", False),
        )
        return user


class UserPhoneNumberSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20, required=True)

    def validate_phone_number(self, value):
        if not value.startswith("+"):
            raise serializers.ValidationError("Phone number must start with a '+'")

        try:
            return normalize_phone_number(value)
        except ValueError as val_exc:
            raise serializers.ValidationError(str(val_exc))


class VerifyUserPhoneNumberSerializer(UserPhoneNumberSerializer):
    code = serializers.CharField(max_length=6, required=True)


class UserPhonePasswordCreateSerializer(UserPhoneNumberSerializer, serializers.ModelSerializer[UserType]):
    password = PasswordField(write_only=True)

    class Meta:
        model = User
        fields = (
            "phone_number",
            "password",
        )

    def create(self, validated_data):
        try:
            user = User.user_manager.create_user_with_phone(
                # important fields here are phone_number and password
                phone_number=validated_data["phone_number"],
                password=validated_data["password"],
                # use phone number as username
                username=validated_data["phone_number"],
                # expecting that the phone number is already verified
                is_verified=True,
                # other fields are optional
                email=validated_data.get("email", None),
                first_name=validated_data.get("first_name", ""),
                last_name=validated_data.get("last_name", ""),
                longitude=validated_data.get("longitude", None),
                latitude=validated_data.get("latitude", None),
                is_client=validated_data.get("is_client", False),
                is_technician=validated_data.get("is_technician", False),
            )
            return user
        except ValueError as val_exc:
            raise serializers.ValidationError(str(val_exc))


class UserUpdateSerializer(serializers.ModelSerializer[UserType]):
    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "longitude",
            "latitude",
        )

        extra_kwargs = {
            "first_name": {"required": False},
            "last_name": {"required": False},
        }

    def update(self, instance, validated_data):
        # Update the user instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(update_fields=validated_data.keys())
        return instance


class UserUpdateProfilePictureSerializer(serializers.ModelSerializer[UserType]):
    profile_picture = serializers.ImageField(allow_null=True, required=False)

    class Meta:
        model = User
        fields = ("profile_picture",)

    def update(self, instance, validated_data):
        if validated_data.get("profile_picture"):
            instance.profile_picture = validated_data["profile_picture"]
            instance.save(update_fields=["profile_picture"])
        return instance


class VerifyUserSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=255)
    code = serializers.CharField(max_length=6)


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255, required=True)
    password = serializers.CharField(min_length=8, required=True)
    device_type = serializers.ChoiceField(choices=Device.OS_CHOICES, required=True)
    device_token = serializers.CharField(min_length=8, required=True)


class UserLogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)
    device_type = serializers.ChoiceField(choices=Device.OS_CHOICES, required=True)
    device_token = serializers.CharField(min_length=8, required=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ErrorResponseChildSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=20)
    message = serializers.CharField(max_length=255)
    details = serializers.CharField(max_length=255)


class ErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=False)
    error = serializers.ListField(child=ErrorResponseChildSerializer())


class ClientCreateSerializer(serializers.ModelSerializer[Client]):
    user = UserCreateSerializer()
    account_type = serializers.ChoiceField(choices=Client.ACCOUNT_TYPE_CHOICES, default=Client.INDIVIDUAL.lower())

    class Meta:
        model = Client
        fields = (
            "user",
            "account_type",
        )

    def create(self, validated_data):
        # Extract the user data from the validated data
        user_data = validated_data.pop("user")

        # get user serializer
        user_serializer = UserCreateSerializer(data=user_data)

        # Validate the user data
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save(is_client=True)

        # Create the technician
        client = Client.objects.create(user=user, **validated_data)
        return client


class ClientPhonePasswordCreateSerializer(serializers.ModelSerializer[Client]):
    user = UserPhonePasswordCreateSerializer()

    class Meta:
        model = Client
        fields = ("user",)

    def create(self, validated_data):
        # Extract the user data from the validated data
        user_data = validated_data.pop("user")

        # get user serializer
        user_serializer = UserPhonePasswordCreateSerializer(data=user_data)

        # Validate the user data
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save(is_client=True)

        # Create the client
        client = Client.objects.create(user=user, account_type=Client.INDIVIDUAL.lower())
        return client


class ClientUpdateSerializer(ClientCreateSerializer):
    user = UserUpdateSerializer()

    class Meta:
        model = Client
        fields = (
            "user",
            "account_type",
            "address",
        )

    def update(self, instance, validated_data):
        if validated_data.get("user"):
            # Update Nested User Field
            user = cast(UserType, instance.user)
            user_serializer = UserUpdateSerializer(user, validated_data.pop("user"), partial=True)
            if user_serializer.is_valid():
                user_serializer.save()

        return super().update(instance, validated_data)


class ClientReadSerializer(serializers.ModelSerializer[Client]):
    user = UserReadSerializer()

    class Meta:
        model = Client
        exclude = ["is_deleted", "id", "created_at", "updated_at"]


class TechnicianCertificateSerializer(serializers.ModelSerializer[TechnicianCertificate]):
    file = serializers.FileField(required=True)

    class Meta:
        model = TechnicianCertificate
        fields = ("file",)

    def is_valid(self, raise_exception: bool = True) -> bool:
        # check if file is valid
        if not self.initial_data.get("file"):
            raise serializers.ValidationError({"file": "This field is required."})

        return super().is_valid(raise_exception)

    def create(self, validated_data):
        # get technician as request user
        technician = cast(Technician, self.context["request"].user)
        certificate = TechnicianCertificate.objects.create(
            technician=technician,
            file=validated_data["file"],
        )
        return certificate


class TechnicianCreateSerializer(serializers.Serializer[Technician]):
    user = UserCreateSerializer()

    def create(self, validated_data):
        # Extract the user data from the validated data
        user_data = validated_data.pop("user")

        # get user serializer
        user_serializer = UserCreateSerializer(data=user_data)

        # Validate the user data
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save(is_technician=True)

        # Create the technician
        technician = Technician.objects.create(user=user, **validated_data)
        return technician


class TechnicianPhonePasswordCreateSerializer(serializers.ModelSerializer[Technician]):
    user = UserPhonePasswordCreateSerializer()

    class Meta:
        model = Technician
        fields = ("user",)

    def create(self, validated_data):
        # Extract the user data from the validated data
        user_data = validated_data.pop("user")

        # get user serializer
        user_serializer = UserPhonePasswordCreateSerializer(data=user_data)

        # Validate the user data
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save(is_technician=True)

        # Create the technician
        technician = Technician.objects.create(user=user)
        return technician


class TechnicianUpdateSerializer(serializers.ModelSerializer[Technician]):
    user = UserUpdateSerializer()

    certificates = serializers.ListField(
        child=serializers.FileField(write_only=True, allow_empty_file=True, required=False),
        write_only=True,
        allow_empty=True,
        required=False,
    )

    class Meta:
        model = Technician
        exclude = ["is_deleted", "id"]

    def to_internal_value(self, data: Any) -> Any:
        internal_data = super().to_internal_value(data)
        # Parse the 'user' field if present
        try:
            if "user" in data:
                internal_data["user"] = json.loads(data["user"])
        except (TypeError, json.JSONDecodeError):
            raise serializers.ValidationError({"user": "Invalid JSON data."})
        return internal_data

    def update(self, instance, validated_data):
        if validated_data.get("user"):
            # Update Nested User Field
            user_serializer = UserUpdateSerializer(instance.user, data=validated_data.pop("user"), partial=True)  # type: ignore # noqa: E501
            if user_serializer.is_valid():
                user_serializer.update(instance.user, user_serializer.validated_data)  # type: ignore # noqa: E501

        if validated_data.get("certificates"):
            # Update Nested Certificates Field
            certificates = validated_data.pop("certificates")
            certificate_objs = [
                TechnicianCertificate(technician=instance, file=certificate) for certificate in certificates
            ]
            TechnicianCertificate.objects.bulk_create(certificate_objs)

            instance.certificates.set(certificate_objs)

        instance = super().update(instance, validated_data)
        return instance


class TechnicianReadSerializer(serializers.ModelSerializer[Technician]):
    user = UserReadSerializer()
    certificates = TechnicianCertificateSerializer(many=True, required=False, read_only=True)

    class Meta:
        model = Technician
        exclude = ["is_deleted", "id", "created_at", "updated_at"]


class TechnicianTypeSerializer(serializers.ModelSerializer[TechnicianType]):
    class Meta:
        model = TechnicianType
        exclude = ["id"]


class TechniciansResponseCountChildSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    result = TechnicianReadSerializer(many=True)


class TechniciansResponseCountSerializer(SuccessResponseSerializer):
    result = TechniciansResponseCountChildSerializer()


class ClientsResponseCountChildSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    result = ClientReadSerializer(many=True)


class ClientsResponseCountSerializer(SuccessResponseSerializer):
    result = ClientsResponseCountChildSerializer()


class TechnicianTypesCountChildSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    result = TechnicianTypeSerializer(many=True)


class TechnicianTypesCountSerializer(serializers.Serializer):
    result = TechnicianTypesCountChildSerializer()


class CustomPasswordTokenSerializer(PasswordTokenSerializer):
    old_password = serializers.CharField(label=_("Current Password"), style={"input_type": "password"})
