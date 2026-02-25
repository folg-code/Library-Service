from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from books.models import Book
from payments.models import Payment


User = get_user_model()


class BorrowingAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="strongpassword123",
            first_name="Test",
            last_name="User",
        )

        self.book = Book.objects.create(
            title="Clean Code",
            author="Robert C. Martin",
            cover=Book.CoverType.SOFT,
            inventory=3,
            daily_fee=Decimal("10.00"),
        )

        token_response = self.client.post(
            reverse("token-obtain"),
            {
                "email": "user@example.com",
                "password": "strongpassword123",
            },
        )

        self.access = token_response.data["access"]
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Authorize {self.access}"
        )

    @patch("borrowings.views.notify_borrowing_created.delay")
    @patch("borrowings.views.create_checkout_session")
    def test_create_borrowing_creates_payment_and_reduces_inventory(
        self,
        mock_checkout,
        mock_notify,
    ):
        mock_session = MagicMock()
        mock_session.id = "session_123"
        mock_session.url = "http://stripe/session"
        mock_checkout.return_value = mock_session

        url = reverse("borrowings-list")

        payload = {
            "book": self.book.id,
            "expected_return_date": (
                date.today() + timedelta(days=5)
            ).isoformat(),
        }

        response = self.client.post(url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 2)

        self.assertEqual(Payment.objects.count(), 1)

        mock_checkout.assert_called_once()
        mock_notify.assert_called_once()