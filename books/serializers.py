from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Book


class BookReadSerializer(serializers.ModelSerializer):
    is_available = serializers.SerializerMethodField(
        help_text="Indicates whether the book is currently available for borrowing."
    )

    class Meta:
        model = Book
        fields = (
            "id",
            "title",
            "author",
            "cover",
            "daily_fee",
            "is_available",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.BooleanField)
    def get_is_available(self, obj):
        return obj.inventory > 0


class BookWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = (
            "title",
            "author",
            "cover",
            "inventory",
            "daily_fee",
        )
        extra_kwargs = {
            "title": {"help_text": "Title of the book"},
            "author": {"help_text": "Author of the book"},
            "cover": {"help_text": "Cover type (e.g., HARD, SOFT)"},
            "inventory": {"help_text": "Number of available copies"},
            "daily_fee": {"help_text": "Daily borrowing fee"},
        }

    def validate_inventory(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Inventory cannot be negative."
            )
        return value

    def validate_daily_fee(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Daily fee must be greater than zero."
            )
        return value