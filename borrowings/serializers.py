from django.db import transaction
from rest_framework import serializers
from django.utils.timezone import now

from books.models import Book
from notifications.tasks import notify_borrowing_created
from payments.models import Payment
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

        request = self.context.get("request")

        if request:
            user = request.user

            has_pending_payment = Payment.objects.filter(
                borrowing__user=user,
                status=Payment.Status.PENDING,
            ).exists()

            if has_pending_payment:
                raise serializers.ValidationError(
                    "You have pending payments. Complete them before borrowing new books."
                )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        book = validated_data["book"]
        user = self.context["request"].user

        book.inventory -= 1
        book.save(update_fields=["inventory"])

        borrowing = Borrowing.objects.create(
            user=user,
            borrow_date=now().date(),
            **validated_data
        )

        notify_borrowing_created.delay(borrowing.id)

        return borrowing


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