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

    # =====================================================
    # CREATE BORROWING
    # =====================================================

    @patch("borrowings.views.notify_borrowing_created.delay")
    @patch("borrowings.views.create_checkout_session")
    def test_create_borrowing_creates_payment_and_reduces_inventory(
            self,
            mock_checkout,
            mock_notify_created,
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
        # on_commit nie wywoła się w trakcie testu — więc nie asercjujemy notify


    # =====================================================
    # RETURN OVERDUE → FINE
    # =====================================================

    @patch("borrowings.views.notify_borrowing_returned.delay")
    @patch("borrowings.views.notify_overdue_fine_created.delay")
    @patch("borrowings.views.create_checkout_session")
    def test_return_overdue_creates_fine(
        self,
        mock_checkout,
        mock_notify_fine,
        mock_notify_returned,
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
                "expected_return_date": (
                    date.today() + timedelta(days=1)
                ).isoformat(),
            },
        )

        borrowing = Borrowing.objects.get(id=create_response.data["id"])

        # make it overdue
        borrowing.expected_return_date = date.today() - timedelta(days=2)
        borrowing.save()

        return_url = reverse(
            "borrowings-return-book",
            args=[borrowing.id],
        )

        response = self.client.post(return_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(
            Payment.objects.filter(
                type=Payment.Type.FINE
            ).exists()
        )

        mock_checkout.assert_called()


    # =====================================================
    # BLOCK BORROWING IF PENDING PAYMENT EXISTS
    # =====================================================

    @patch("borrowings.views.create_checkout_session")
    def test_cannot_create_borrowing_when_pending_payment_exists(
        self,
        mock_checkout,
    ):
        mock_session = MagicMock()
        mock_session.id = "session_123"
        mock_session.url = "http://stripe/session"
        mock_checkout.return_value = mock_session

        url = reverse("borrowings-list")

        payload = {
            "book": self.book.id,
            "expected_return_date": (
                date.today() + timedelta(days=3)
            ).isoformat(),
        }

        # First borrowing (creates pending payment)
        first_response = self.client.post(url, payload)
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)

        # Second borrowing should fail
        second_response = self.client.post(url, payload)

        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("pending", str(second_response.data).lower())


# =====================================================
# QUERYSET TESTS
# =====================================================

class BorrowingQuerysetTests(APITestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(
            email="user1@example.com",
            password="password123",
        )

        self.user2 = User.objects.create_user(
            email="user2@example.com",
            password="password123",
        )

        self.staff = User.objects.create_user(
            email="admin@example.com",
            password="password123",
            is_staff=True,
        )

        self.book = Book.objects.create(
            title="Test Book",
            author="Author",
            cover=Book.CoverType.SOFT,
            inventory=5,
            daily_fee=Decimal("5.00"),
        )

        self.borrowing1 = Borrowing.objects.create(
            user=self.user1,
            book=self.book,
            expected_return_date=date.today() + timedelta(days=3),
        )

        self.borrowing2 = Borrowing.objects.create(
            user=self.user2,
            book=self.book,
            expected_return_date=date.today() + timedelta(days=3),
        )

    def authenticate(self, user):
        token = self.client.post(
            reverse("token-obtain"),
            {"email": user.email, "password": "password123"},
        ).data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Authorize {token}")

    def test_user_sees_only_own_borrowings(self):
        self.authenticate(self.user1)

        response = self.client.get(reverse("borrowings-list"))

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.borrowing1.id)

    def test_staff_sees_all_borrowings(self):
        self.authenticate(self.staff)

        response = self.client.get(reverse("borrowings-list"))

        self.assertEqual(len(response.data), 2)