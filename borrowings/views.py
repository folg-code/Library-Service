from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.timezone import now
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from notifications.tasks import (
    notify_borrowing_created,
    notify_borrowing_returned,
    notify_overdue_fine_created
)
from .models import Borrowing
from .serializers import (
    BorrowingReadSerializer,
    BorrowingCreateSerializer,
    BorrowingReturnSerializer,
)
from books.models import Book

from payments.models import Payment
from payments.services import create_checkout_session
from .services import calculate_overdue_days

@extend_schema_view(
    list=extend_schema(
        summary="List borrowings",
        description=(
            "Return list of borrowings.\n\n"
            "Non-admin users can see only their own borrowings.\n"
            "Admin users can filter by user_id.\n\n"
            "Filters:\n"
            "- is_active=true → borrowings not returned yet\n"
            "- is_active=false → already returned borrowings\n"
        ),
        parameters=[
            OpenApiParameter(
                name="user_id",
                description="Filter by user id (admin only)",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="is_active",
                description="Filter by active borrowings",
                required=False,
                type=bool,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve borrowing",
        description="Retrieve detailed information about a specific borrowing."
    ),
    create=extend_schema(
        summary="Create borrowing",
        description=(
            "Create a new borrowing.\n\n"
            "Business rules:\n"
            "- Book inventory must be greater than 0\n"
            "- User must not have any PENDING payments\n"
            "- Inventory decreases by 1\n"
            "- Stripe Checkout session is created\n"
            "- PAYMENT record is created with status=PENDING\n"
            "- Notification is sent asynchronously\n"
        ),
        examples=[
            OpenApiExample(
                "Create borrowing example",
                value={
                    "book": 1,
                    "expected_return_date": "2026-03-10"
                },
            )
        ],
    ),
)
class BorrowingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        read_serializer = BorrowingReadSerializer(
            serializer.instance,
            context=self.get_serializer_context(),
        )

        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        with transaction.atomic():
            book = Book.objects.select_for_update().get(
                id=serializer.validated_data["book"].id
            )

            if book.inventory <= 0:
                raise ValidationError("Book is not available.")

            book.inventory -= 1
            book.save()

            borrowing = serializer.save(
                user=self.request.user,
                borrow_date=now().date(),
            )

            amount = int(book.daily_fee * Decimal("100"))

            try:
                session = create_checkout_session(
                    borrowing=borrowing,
                    amount=amount,
                )
            except Exception:
                raise APIException("Payment provider error")

            Payment.objects.create(
                borrowing=borrowing,
                type=Payment.Type.PAYMENT,
                money_to_pay=book.daily_fee,
                session_url=session.url,
                session_id=session.id,
            )

            transaction.on_commit(
                lambda: notify_borrowing_created.delay(borrowing.id)
            )

    @extend_schema(
        summary="Return borrowed book",
        description=(
                "Mark borrowing as returned.\n\n"
                "Business rules:\n"
                "- Cannot return twice\n"
                "- actual_return_date is set automatically\n"
                "- Book inventory increases by 1\n"
                "- If returned after expected_return_date → FINE payment is created\n"
                "- Fine amount = overdue_days * daily_fee * FINE_MULTIPLIER\n"
                "- Stripe Checkout session created for fine\n"
                "- Notifications are sent asynchronously\n"
        ),
        responses={
            200: BorrowingReadSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    @action(methods=["post"], detail=True, url_path="return")
    @action(methods=["post"], detail=True, url_path="return")
    def return_book(self, request, pk=None):

        borrowing = self.get_object()
        serializer = self.get_serializer(borrowing, data=request.data)
        serializer.is_valid(raise_exception=True)

        if borrowing.actual_return_date:
            raise ValidationError("Book already returned.")

        with transaction.atomic():
            returned_date = now().date()
            borrowing.actual_return_date = returned_date
            borrowing.save(update_fields=["actual_return_date"])

            book = Book.objects.select_for_update().get(id=borrowing.book.id)
            book.inventory += 1
            book.save(update_fields=["inventory"])

            overdue_days = calculate_overdue_days(
                expected=borrowing.expected_return_date,
                returned=returned_date,
            )

            if overdue_days > 0:
                fine_amount = (
                        Decimal(overdue_days)
                        * book.daily_fee
                        * Decimal(settings.FINE_MULTIPLIER)
                )

                session = create_checkout_session(
                    borrowing=borrowing,
                    amount=int(fine_amount * 100),
                )

                Payment.objects.create(
                    borrowing=borrowing,
                    type=Payment.Type.FINE,
                    money_to_pay=fine_amount,
                    session_id=session.id,
                    session_url=session.url,
                )

                transaction.on_commit(
                    lambda: notify_overdue_fine_created.delay(borrowing.id)
                )

        transaction.on_commit(
            lambda: notify_borrowing_returned.delay(borrowing.id)
        )

        return Response(
            BorrowingReadSerializer(borrowing).data,
            status=status.HTTP_200_OK,
        )
