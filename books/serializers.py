from rest_framework import serializers
from .models import Book


class BookReadSerializer(serializers.ModelSerializer):
    is_available = serializers.SerializerMethodField()

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

    def get_is_available(self, obj):
        return obj.inventory > 0