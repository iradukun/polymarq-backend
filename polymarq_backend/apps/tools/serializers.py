from typing import Any

from djmoney.contrib.django_rest_framework import MoneyField
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from polymarq_backend.apps.tools.models import RentalRequest, Tool, ToolCategory, ToolImage, ToolNegotiation
from polymarq_backend.apps.users.api.serializers import TechnicianReadSerializer, UserReadSerializer
from polymarq_backend.apps.users.models import Technician
from polymarq_backend.apps.users.utils import get_custom_user_model

User = get_custom_user_model()


class ToolCategorySerializer(serializers.ModelSerializer):
    number_of_tools = serializers.SerializerMethodField()

    class Meta:
        model = ToolCategory
        exclude = ("created_at", "updated_at", "created_by", "id")

    def get_number_of_tools(self, obj: ToolCategory) -> int:
        return obj.tools.filter(is_deleted=False).count()  # type: ignore


class ToolCategoryResponseCountSerializer(serializers.Serializer):
    result = ToolCategorySerializer(many=True)
    count = serializers.IntegerField()


class ToolImageCreateSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(write_only=True)

    class Meta:
        model = ToolImage
        fields = ("image",)
        read_only_fields = ("created_at", "updated_at")

    def create(self, validated_data: Any) -> Any:
        try:
            technician = Technician.objects.get(user=self.context["request"].user)
            validated_data["created_by"] = technician
        except Technician.DoesNotExist:
            raise serializers.ValidationError("Technician does not exist")
        return super().create(validated_data)


class ToolImageReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ToolImage
        fields = ("image",)
        read_only_fields = ("created_at", "updated_at")


class ToolCreateSerializer(serializers.ModelSerializer):
    category = serializers.CharField(write_only=True, help_text="The tool's category name")
    images = serializers.ListField(
        child=serializers.ImageField(write_only=True),
        write_only=True,
        required=False,
    )
    color_codes = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Tool
        exclude = (
            "is_deleted",
            "owner",
            "is_rented",
            "is_available",
        )
        read_only_fields = ("created_at", "updated_at")

    def create(self, validated_data: Any) -> Any:
        category_name = validated_data["category"].strip().lower()

        try:
            category_instance = ToolCategory.objects.get(name__iexact=category_name)
            validated_data["category"] = category_instance
        except ToolCategory.DoesNotExist:
            category_instance = ToolCategory.objects.get(name__iexact="others")
            validated_data["category"] = category_instance

        images = validated_data.pop("images", [])
        color_codes = validated_data.pop("color_codes", [])
        tool = Tool.objects.create(**validated_data)

        # create images
        tool.set_color_codes(color_codes)
        tool_images = [ToolImage(image=image, created_by=validated_data.get("owner", None)) for image in images]
        ToolImage.objects.bulk_create(tool_images)
        # set images
        tool.images.set(tool_images)
        return tool


class ToolUpdateSerializer(serializers.ModelSerializer):
    # category = serializers.UUIDField(write_only=True, required=False)

    images = serializers.ListField(
        child=serializers.ImageField(write_only=True),
        write_only=True,
        required=False,
    )
    color_codes = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Tool
        exclude = ("is_deleted", "owner", "category")
        read_only_fields = (
            "uuid",
            "created_at",
            "updated_at",
        )

    def update(self, instance: Tool, validated_data):
        # Extract color_codes from validated_data and update them using the model method
        color_codes = validated_data.pop("color_codes", [])
        images = validated_data.pop("images", [])
        instance = super().update(instance, validated_data)
        tool_images = [ToolImage(image=image, created_by=validated_data.get("owner", None)) for image in images]
        ToolImage.objects.bulk_create(tool_images)
        instance.set_color_codes(color_codes)
        instance.images.set(tool_images)
        return instance


class ToolReadSerializer(serializers.ModelSerializer):
    owner = TechnicianReadSerializer()
    category = ToolCategorySerializer()
    images = ToolImageReadSerializer(many=True)
    color_codes = serializers.SerializerMethodField()

    class Meta:
        model = Tool
        exclude = (
            "is_deleted",
            "id",
            "created_at",
            "updated_at",
        )

    def get_color_codes(self, obj: Tool) -> list[str]:
        return obj.get_color_codes()


class ToolsResponseCountSerializer(serializers.Serializer):
    result = ToolReadSerializer(many=True)
    count = serializers.IntegerField()


class RentalRequestCreateSerializer(serializers.ModelSerializer):
    tool = serializers.UUIDField(write_only=True, help_text="tool uuid")

    def __init__(self, instance: Any = None, user: Technician | None = None, **kwargs):  # type: ignore
        self.request_owner = user
        super().__init__(instance, **kwargs)

    class Meta:
        model = RentalRequest
        exclude = (
            "request_owner",
            "is_deleted",
            "request_status",
        )

    def is_valid(self, raise_exception: bool = False) -> bool:
        valid = super().is_valid(raise_exception=raise_exception)

        if not self.request_owner:
            return valid

        # Checking for existing requests
        requests = self.Meta.model.objects.filter(
            request_owner=self.request_owner.pk,
            tool__uuid=self.initial_data["tool"],  # type: ignore
            is_deleted=False,
        )
        if requests.exists():
            raise ValidationError("Request already exists")

        return valid

    def create(self, validated_data: Any) -> Any:
        try:
            tool_instance = Tool.objects.get(uuid=validated_data["tool"], is_deleted=False)
            validated_data["tool"] = tool_instance
        except Tool.DoesNotExist:
            raise serializers.ValidationError("Tool does not exists")

        return super().create(validated_data)


class RentalRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalRequest
        exclude = (
            "is_deleted",
            "request_owner",
            "tool",
        )


class RentalRequestReadSerializer(serializers.ModelSerializer):
    tool = serializers.SerializerMethodField()
    request_owner = TechnicianReadSerializer()

    class Meta:
        model = RentalRequest
        exclude = (
            "is_deleted",
            "id",
        )

    def get_tool(self, obj: RentalRequest) -> str:
        return obj.tool.uuid.__str__()


class RentalRequestCountResponseSerializer(serializers.Serializer):
    data = RentalRequestReadSerializer(many=True)  # type: ignore
    count = serializers.IntegerField()


class ToolNegotiationCreateSerializer(serializers.Serializer):
    tool_uuid = serializers.UUIDField(write_only=True, help_text="tool uuid")
    offered_price = MoneyField(max_digits=14, decimal_places=2, required=True, write_only=True)


class ToolNegotiationReadSerializer(serializers.ModelSerializer[ToolNegotiation]):
    tool = ToolReadSerializer()
    negotiator = UserReadSerializer()

    class Meta:
        model = ToolNegotiation
        fields = ("uuid", "tool", "negotiator", "offered_price", "status")


class ToolNegotiationResponseSerializer(serializers.Serializer):
    negotiation_uuid = serializers.UUIDField(write_only=True, help_text="negotiation uuid")
    status = serializers.ChoiceField(choices=ToolNegotiation.STATUS_CHOICES, default=ToolNegotiation.ACCEPTED)
