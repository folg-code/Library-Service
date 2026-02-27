from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import TestCase

from books.models import Book
from borrowings.models import Borrowing


class BorrowingModelTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user@test.com",
            password="password123"
        )

        self.book = Book.objects.create(
            title="Test Book",
            author="Author",
            cover=Book.CoverType.SOFT,
            inventory=3,
            daily_fee=Decimal("2.00"),
        )

        self.today = date.today()
        self.future_date = self.today + timedelta(days=7)
        self.past_date = self.today - timedelta(days=1)

    def test_create_valid_borrowing(self):
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return_date=self.future_date,
        )

        self.assertEqual(borrowing.user, self.user)
        self.assertEqual(borrowing.book, self.book)
        self.assertEqual(borrowing.borrow_date, self.today)
        self.assertEqual(borrowing.expected_return_date, self.future_date)
        self.assertIsNone(borrowing.actual_return_date)

    def test_expected_return_date_cannot_be_before_borrow_date(self):
        borrowing = Borrowing(
            user=self.user,
            book=self.book,
            expected_return_date=self.past_date,
        )

        with self.assertRaises(ValidationError):
            borrowing.full_clean()

    def test_actual_return_date_cannot_be_before_borrow_date(self):
        borrowing = Borrowing(
            user=self.user,
            book=self.book,
            expected_return_date=self.future_date,
            actual_return_date=self.past_date,
        )

        with self.assertRaises(ValidationError):
            borrowing.full_clean()

    def test_actual_return_date_can_be_equal_or_after_borrow_date(self):
        borrowing = Borrowing(
            user=self.user,
            book=self.book,
            expected_return_date=self.future_date,
            actual_return_date=self.today,
        )

        borrowing.full_clean()

    def test_is_active_returns_true_when_not_returned(self):
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return_date=self.future_date,
        )

        self.assertTrue(borrowing.is_active)

    def test_is_active_returns_false_when_returned(self):
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return_date=self.future_date,
            actual_return_date=self.today,
        )

        self.assertFalse(borrowing.is_active)

    def test_borrowings_are_ordered_by_borrow_date_desc(self):
        borrowing1 = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return_date=self.future_date,
        )

        borrowing2 = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return_date=self.future_date,
        )

        borrowings = list(Borrowing.objects.all())

        self.assertEqual(borrowings[0], borrowing2)
        self.assertEqual(borrowings[1], borrowing1)

    def test_str_representation(self):
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return_date=self.future_date,
        )

        self.assertIn("borrowed", str(borrowing))
        self.assertIn(str(self.book), str(borrowing))
