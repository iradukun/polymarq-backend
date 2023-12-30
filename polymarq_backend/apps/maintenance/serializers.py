from rest_framework import serializers

from polymarq_backend.apps.maintenance.models import Maintenance
from polymarq_backend.apps.users.api.serializers import (
    ClientReadSerializer,
    TechnicianReadSerializer,
    TechnicianTypeSerializer,
)
from polymarq_backend.apps.users.models import TechnicianType
from polymarq_backend.core.success_response import SuccessResponseSerializer
from polymarq_backend.core.utils.main import CurrentClient


class MaintenanceCreateSerializer(serializers.ModelSerializer[Maintenance]):
    client = serializers.HiddenField(default=CurrentClient())
    frequency = serializers.ChoiceField(choices=Maintenance.FREQUENCY, default=Maintenance.WEEKLY)
    technician_type = serializers.CharField(max_length=255)

    class Meta:
        model = Maintenance
        read_only_fields = ["uuid", "created_at", "updated_at"]
        exclude = ["id", "is_deleted", "technician"]

    def create(self, validated_data):
        """
        create method for the MaintenanceCreateSerializer

        enforces a rule that non-existent technician types
        should be created, and existing ones should be reused
        """

        technician_type = validated_data.get("technician_type")
        # check if a technician type object exists with that title
        technician_type_queryset = TechnicianType.objects.filter(title=technician_type.lower())
        if technician_type_queryset:
            # get the actual technician type object
            technician_type = technician_type_queryset.first()
        else:
            # create a new technician type object
            technician_type = TechnicianType.objects.create(title=technician_type.lower())
        validated_data.pop("technician_type")

        return Maintenance.objects.create(technician_type=technician_type, **validated_data)

    def to_representation(self, instance):
        """
        The initial serializer method field for 'technician_type' accepts a charfield
        but we want to return the properties of the field, not just the obect id.
        That is what this method solves
        """
        representation = super().to_representation(instance)
        # At this step, representation['technician_type'] is a string title of the object.
        # In the next step, I use the TechnicianTypeSerializer to overwrite that
        # with serialized data for the technician_type object.
        representation["technician_type"] = TechnicianTypeSerializer(instance.technician_type).data
        return representation


class MaintenanceReadSerializer(serializers.ModelSerializer[Maintenance]):
    client = ClientReadSerializer()
    technician_type = TechnicianTypeSerializer()
    technician = TechnicianReadSerializer()

    class Meta:
        model = Maintenance
        read_only_fields = ["uuid", "created_at", "updated_at"]
        exclude = ["id", "is_deleted"]


class MaintenanceResponseCountChildSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    result = MaintenanceReadSerializer(many=True)


class MaintenanceResponseCountSerializer(SuccessResponseSerializer):
    result = MaintenanceResponseCountChildSerializer()


class MaintenanceUpdateSerializer(serializers.ModelSerializer[Maintenance]):
    client = serializers.HiddenField(default=CurrentClient())
    frequency = serializers.ChoiceField(choices=Maintenance.FREQUENCY, default=Maintenance.WEEKLY)
    technician_type = serializers.CharField(max_length=255)

    class Meta:
        model = Maintenance
        read_only_fields = ["uuid", "created_at", "updated_at"]
        exclude = ["id", "is_deleted"]

    def to_representation(self, instance):
        """
        The initial serializer method field for 'technician_type' accepts a charfield
        but we want to return the properties of the field, not just the obect id.
        That is what this method solves
        """
        representation = super().to_representation(instance)
        # At this step, representation['technician_type'] is a string title of the object.
        # In the next step, I use the TechnicianTypeSerializer to overwrite that
        # with serialized data for the technician_type object.
        representation["technician_type"] = TechnicianTypeSerializer(instance.technician_type).data
        representation["technician"] = TechnicianReadSerializer(instance.technician).data
        return representation
