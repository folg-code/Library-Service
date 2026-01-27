from decimal import Decimal

from django.db import transaction
from django.utils.timezone import now
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Borrowing
from .serializers import (
    BorrowingReadSerializer,
    BorrowingCreateSerializer,
    BorrowingReturnSerializer,
)
from books.models import Book

from payments.models import Payment
from payments.services import create_checkout_session



class BorrowingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Borrowing.objects.select_related("book", "user")

        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)

        user_id = self.request.query_params.get("user_id")
        is_active = self.request.query_params.get("is_active")

        if user_id and self.request.user.is_staff:
            queryset = queryset.filter(user_id=user_id)

        if is_active is not None:
            queryset = queryset.filter(
                actual_return_date__isnull=is_active.lower() == "true"
            )

        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return BorrowingCreateSerializer
        if self.action == "return_book":
            return BorrowingReturnSerializer
        return BorrowingReadSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            book = Book.objects.select_for_update().get(
                id=serializer.validated_data["book"].id
            )

            if book.inventory <= 0:
                raise ValueError("Book is not available.")

            book.inventory -= 1
            book.save()

            borrowing = serializer.save(
                user=self.request.user,
                borrow_date=now().date(),
            )

            amount = int(book.daily_fee * Decimal("100"))

            session = create_checkout_session(
                borrowing=borrowing,
                amount=amount,
            )

            Payment.objects.create(
                borrowing=borrowing,
                type=Payment.Type.PAYMENT,
                money_to_pay=book.daily_fee,
                session_url=session.url,
                session_id=session.id,
            )

    @action(
        methods=["post"],
        detail=True,
        url_path="return",
    )
    def return_book(self, request, pk=None):
        borrowing = self.get_object()
        serializer = self.get_serializer(
            borrowing,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            borrowing.actual_return_date = now().date()
            borrowing.save()

            book = Book.objects.select_for_update().get(
                id=borrowing.book.id
            )
            book.inventory += 1
            book.save()

        return Response(
            BorrowingReadSerializer(borrowing).data,
            status=status.HTTP_200_OK,
        )