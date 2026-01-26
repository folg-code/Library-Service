from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.timezone import now

from books.models import Book
from borrowings.models import Borrowing
from borrowings.serializers import (
    BorrowingReadSerializer,
    BorrowingCreateSerializer,
    BorrowingReturnSerializer,
)


class BorrowingReadSerializerTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user@test.com",
            password="password123",
        )

        self.book = Book.objects.create(
            title="Test Book",
            author="Author",
            cover=Book.CoverType.SOFT,
            inventory=2,
            daily_fee=Decimal("2.00"),
        )

        self.borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return_date=date.today() + timedelta(days=5),
        )


    def test_is_active_is_true_when_not_returned(self):
        serializer = BorrowingReadSerializer(self.borrowing)
        self.assertTrue(serializer.data["is_active"])



class BorrowingCreateSerializerTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user@test.com",
            password="password123",
        )

        self.book = Book.objects.create(
            title="Available Book",
            author="Author",
            cover=Book.CoverType.SOFT,
            inventory=1,
            daily_fee=Decimal("1.50"),
        )

    def test_create_serializer_valid_data(self):
        data = {
            "book": self.book.id,
            "expected_return_date": (now().date() + timedelta(days=3)).isoformat(),
        }

        serializer = BorrowingCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_expected_return_date_must_be_in_future(self):
        data = {
            "book": self.book.id,
            "expected_return_date": now().date().isoformat(),
        }

        serializer = BorrowingCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("expected_return_date", serializer.errors)

    def test_cannot_borrow_book_with_zero_inventory(self):
        self.book.inventory = 0
        self.book.save()

        data = {
            "book": self.book.id,
            "expected_return_date": (now().date() + timedelta(days=3)).isoformat(),
        }

        serializer = BorrowingCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("Book is not available.", str(serializer.errors))


class BorrowingReturnSerializerTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user@test.com",
            password="password123",
        )

        self.book = Book.objects.create(
            title="Returnable Book",
            author="Author",
            cover=Book.CoverType.SOFT,
            inventory=1,
            daily_fee=Decimal("2.00"),
        )

        self.borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return_date=date.today() + timedelta(days=2),
        )

    def test_return_serializer_valid_when_not_returned(self):
        data = {
            "actual_return_date": now().date().isoformat()
        }

        serializer = BorrowingReturnSerializer(
            instance=self.borrowing,
            data=data,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_cannot_return_borrowing_twice(self):
        self.borrowing.actual_return_date = now().date()
        self.borrowing.save()

        data = {
            "actual_return_date": now().date().isoformat()
        }

        serializer = BorrowingReturnSerializer(
            instance=self.borrowing,
            data=data,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)