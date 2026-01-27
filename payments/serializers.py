from rest_framework import serializers
from .models import Payment


class PaymentReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            "id",
            "borrowing",
            "type",
            "status",
            "money_to_pay",
            "session_url",
            "created_at",
        )
        read_only_fields = fields