from decimal import Decimal
from django.urls import reverse
from django.conf import settings
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
from datetime import date, timedelta

from users.models import User
from books.models import Book
from borrowings.models import Borrowing
from payments.models import Payment

from django.test import override_settings
from unittest.mock import patch, MagicMock


@override_settings(
    STRIPE_SUCCESS_URL="http://test/success/",
    STRIPE_CANCEL_URL="http://test/cancel/",
    FINE_MULTIPLIER=2,
)
class BorrowingReturnAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@test.com",
            password="password123"
        )

        self.book = Book.objects.create(
            title="Test Book",
            author="Author",
            cover="HARD",
            inventory=3,
            daily_fee=Decimal("10.00"),
        )

        self.borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            borrow_date=date.today(),
            expected_return_date=date.today() + timedelta(days=3),
        )

        self.url = reverse("borrowings-return-book", args=[self.borrowing.id])
        self.client.force_authenticate(self.user)

    def test_return_success(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.borrowing.refresh_from_db()
        self.assertIsNotNone(self.borrowing.actual_return_date)

        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 4)

        self.assertEqual(Payment.objects.filter(type=Payment.Type.FINE).count(), 0)

    def test_double_return_returns_400(self):
        self.client.post(self.url)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("borrowings.views.create_checkout_session")
    def test_overdue_return_creates_fine(self, mock_checkout):
        mock_session = MagicMock()
        mock_session.id = "fine_session"
        mock_session.url = "http://stripe/fine"
        mock_checkout.return_value = mock_session

        self.borrowing.expected_return_date = date.today() - timedelta(days=3)
        self.borrowing.save()

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        fine = Payment.objects.filter(type=Payment.Type.FINE).first()
        self.assertIsNotNone(fine)

        expected_amount = (
            3 *
            self.book.daily_fee *
            settings.FINE_MULTIPLIER
        )

        self.assertEqual(fine.money_to_pay, expected_amount)
        self.assertEqual(fine.status, Payment.Status.PENDING)