from rest_framework import serializers

from polymarq_backend.apps.payments.mixins import PaymentTransactionMixin
from polymarq_backend.apps.payments.models import Bank, JobIncrementalPayment, TechnicianBankAccount, ToolPurchase


class JobIncrementalPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobIncrementalPayment
        fields = "__all__"


class JobStateSerializer(serializers.Serializer):
    job_state = serializers.FloatField()


class JobIncrementalPaymentCountSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    data = JobIncrementalPaymentSerializer(many=True)  # type: ignore


class BankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = ["name", "slug", "code", "longcode"]


class TechnicianBankAccountCreateSerializer(serializers.ModelSerializer[TechnicianBankAccount]):
    bank_slug = serializers.SlugField(
        write_only=True,
        required=True,
        help_text="The slug of the bank to which the account belongs.",
    )

    class Meta:
        model = TechnicianBankAccount
        fields = [
            "bank_slug",
            "account_name",
            "account_number",
        ]


class PaymentTransactionMixinSerializer(serializers.ModelSerializer[PaymentTransactionMixin]):
    quantity = serializers.IntegerField(
        default=1,
        write_only=True,
        help_text="The quantity of the item to be purchased.",
    )
    status = serializers.CharField(
        read_only=True,
        help_text="The status of the transaction.",
    )

    class Meta:
        model = PaymentTransactionMixin
        fields = [
            "quantity",
            "amount",
            "transaction_reference",
            "paid",
            "status",
        ]
        abstract = True


class ToolPurchaseSerializer(PaymentTransactionMixinSerializer):
    tool_uuid = serializers.UUIDField(
        write_only=True,
        required=True,
        help_text="The uuid of the tool to be purchased.",
    )

    class Meta:
        model = ToolPurchase
        fields = ["tool_uuid", "quantity"]
