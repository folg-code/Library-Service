from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from books.models import Book
from borrowings.models import Borrowing
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


    @patch("borrowings.views.notify_borrowing_returned.delay")
    @patch("borrowings.views.notify_overdue_fine_created.delay")
    @patch("borrowings.views.create_checkout_session")
    def test_return_overdue_creates_fine(
        self,
        mock_checkout,
        mock_notify_fine,
        mock_notify_return,
    ):
        mock_session = MagicMock()
        mock_session.id = "fine_session"
        mock_session.url = "http://stripe/fine"
        mock_checkout.return_value = mock_session

        # create borrowing first
        create_response = self.client.post(
            reverse("borrowings-list"),
            {
                "book": self.book.id,
                "expected_return_date": ((date.today() + timedelta(days=1))
                ).isoformat(),
            },
        )

        print(create_response.status_code)
        print(create_response.data)

        borrowing = Borrowing.objects.get(id=create_response.data["id"])
        borrowing.expected_return_date = date.today() - timedelta(days=2)
        borrowing.save()



        borrowing_id = create_response.data["id"]



        return_url = reverse(
            "borrowings-return-book",
            args=[borrowing_id],
        )

        response = self.client.post(return_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(
            Payment.objects.filter(
                type=Payment.Type.FINE
            ).exists()
        )

        mock_notify_fine.assert_called()
        mock_notify_return.assert_called_once()