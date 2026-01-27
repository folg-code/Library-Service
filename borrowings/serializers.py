from rest_framework import serializers
from django.utils.timezone import now

from books.models import Book
from .models import Borrowing
from books.serializers import BookReadSerializer


class BorrowingReadSerializer(serializers.ModelSerializer):
    book = BookReadSerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "book",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "is_active",
        )


class BorrowingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = (
            "book",
            "expected_return_date",
        )

    def validate_expected_return_date(self, value):
        if value <= now().date():
            raise serializers.ValidationError(
                "Expected return date must be in the future."
            )
        return value

    def validate(self, attrs):
        book: Book = attrs["book"]

        if book.inventory <= 0:
            raise serializers.ValidationError(
                "Book is not available."
            )

        return attrs


class BorrowingReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ("actual_return_date",)

    def validate(self, attrs):
        if self.instance.actual_return_date is not None:
            raise serializers.ValidationError(
                "Borrowing has already been returned."
            )
        return attrs