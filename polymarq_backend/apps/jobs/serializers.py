from djmoney.contrib.django_rest_framework import MoneyField
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from polymarq_backend.apps.jobs.models import Job, Ping
from polymarq_backend.apps.users.api.serializers import (  # TechnicianReadSerializer,
    ClientReadSerializer,
    UserReadSerializer,
)
from polymarq_backend.apps.users.models import Technician
from polymarq_backend.core.success_response import SuccessResponseSerializer
from polymarq_backend.core.utils.main import CurrentClient, CurrentTechnician, distance_between_two_points


class JobCreateSerializer(serializers.ModelSerializer[Job]):
    client = serializers.HiddenField(default=CurrentClient())
    status = serializers.ChoiceField(choices=Job.STATUSES, default=Job.PENDING)

    class Meta:
        model = Job
        read_only_fields = ["uuid", "created_at", "updated_at"]
        exclude = [
            "id",
            "technician",
            "is_deleted",
        ]


class JobUpdateSerializer(serializers.ModelSerializer[Job]):
    status = serializers.ChoiceField(choices=Job.STATUSES, default=Job.PENDING)

    class Meta:
        model = Job
        fields = [
            "status",
            "image",
            "require_technicians_immediately",
            "require_technicians_next_day",
        ]

        extra_kwargs = {
            "image": {"required": False},
            "status": {"allow_blank": True},
            "require_technicians_immediately": {"required": False},
            "require_technicians_next_day": {"required": False},
        }


class TechnicianSearchSerializer(serializers.ModelSerializer[Technician]):
    user = UserReadSerializer()
    distance_from_client = serializers.SerializerMethodField()

    class Meta:
        model = Technician
        exclude = ["id", "is_deleted"]

    @extend_schema_field(float)  # type: ignore
    def get_distance_from_client(self, obj):
        """
        Returns the distance [in kilometers]
        between the client and technician
        """
        try:
            lat1 = self.context["request"].user.longitude
            lon1 = self.context["request"].user.latitude
            lat2 = obj.user.longitude
            lon2 = obj.user.latitude
            return distance_between_two_points(lat1, lat2, lon1, lon2)
        except AttributeError:
            return None


class CreatePingSerializer(serializers.ModelSerializer[Ping]):
    client = serializers.HiddenField(default=CurrentClient())
    # status = serializers.ChoiceField(choices=Ping.STATUSES, default=Ping.REQUESTED)
    job_uuid = serializers.UUIDField(required=True, write_only=True)
    technician_uuid = serializers.UUIDField(required=True, write_only=True)
    price_quote = MoneyField(max_digits=14, decimal_places=2, required=False, read_only=True)

    class Meta:
        model = Ping
        read_only_fields = ["uuid", "distance_from_client"]
        exclude = [
            "id",
            "job",
            "technician",
            "created_at",
            "updated_at",
            "transaction_cost",
            "transaction_cost_currency",
        ]


class UpdatePingSerializer(serializers.ModelSerializer[Ping]):
    technician = serializers.HiddenField(default=CurrentTechnician())
    status = serializers.ChoiceField(choices=Ping.STATUSES, default=Ping.ACCEPTED)
    price_quote = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, write_only=True)

    class Meta:
        model = Ping
        fields = ["status", "technician", "price_quote"]


class JobReadSerializer(serializers.ModelSerializer[Job]):
    client = ClientReadSerializer()

    class Meta:
        model = Job
        exclude = ["id", "technician", "is_deleted"]


class JobResponseCountChildSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    result = JobReadSerializer(many=True)


class JobResponseCountSerializer(SuccessResponseSerializer):
    result = JobResponseCountChildSerializer()


class PingReadSerializer(serializers.ModelSerializer[Ping]):
    # technician = TechnicianReadSerializer()
    job = JobReadSerializer()
    # client = ClientReadSerializer()

    class Meta:
        model = Ping
        exclude = [
            "id",
        ]


class InitialJobPaymentSerializer(serializers.Serializer):
    job_uuid = serializers.UUIDField(required=True, write_only=True)
