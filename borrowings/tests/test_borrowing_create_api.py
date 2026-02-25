from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.urls import reverse
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework import status

from users.models import User
from books.models import Book
from borrowings.models import Borrowing
from payments.models import Payment


@override_settings(
    STRIPE_SUCCESS_URL="http://test/success/",
    STRIPE_CANCEL_URL="http://test/cancel/",
    FINE_MULTIPLIER=2,
)
class BorrowingCreateAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@test.com",
            password="password123"
        )

        self.book = Book.objects.create(
            title="Test Book",
            author="Author",
            cover="HARD",
            inventory=5,
            daily_fee=Decimal("10.00"),
        )

        self.url = reverse("borrowings-list")

    # ============================================================
    # CREATE SUCCESS
    # ============================================================

    @patch("borrowings.views.notify_borrowing_created.delay")
    @patch("borrowings.views.create_checkout_session")
    def test_create_borrowing_success(
        self,
        mock_create_checkout,
        mock_notify_created,
    ):
        mock_session = MagicMock()
        mock_session.id = "sess_123"
        mock_session.url = "http://stripe.test"
        mock_create_checkout.return_value = mock_session

        self.client.force_authenticate(self.user)

        response = self.client.post(
            self.url,
            {
                "book": self.book.id,
                "expected_return_date": "2030-01-01"
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 4)

        self.assertEqual(Borrowing.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)

        payment = Payment.objects.first()
        self.assertEqual(payment.type, Payment.Type.PAYMENT)
        self.assertEqual(payment.status, Payment.Status.PENDING)

        mock_create_checkout.assert_called_once()

    # ============================================================
    # STRIPE FAILURE → ATOMIC ROLLBACK
    # ============================================================

    @patch("borrowings.views.create_checkout_session")
    def test_create_is_atomic_when_stripe_fails(self, mock_create_checkout):
        mock_create_checkout.side_effect = Exception("Stripe failure")

        self.client.force_authenticate(self.user)

        response = self.client.post(
            self.url,
            {
                "book": self.book.id,
                "expected_return_date": "2030-01-01"
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 5)

        self.assertEqual(Borrowing.objects.count(), 0)
        self.assertEqual(Payment.objects.count(), 0)

    # ============================================================
    # INVENTORY ZERO
    # ============================================================

    def test_inventory_zero_returns_400(self):
        self.book.inventory = 0
        self.book.save()

        self.client.force_authenticate(self.user)

        response = self.client.post(
            self.url,
            {
                "book": self.book.id,
                "expected_return_date": "2030-01-01"
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Borrowing.objects.count(), 0)
        self.assertEqual(Payment.objects.count(), 0)

    # ============================================================
    # PENDING PAYMENT BLOCKS BORROWING
    # ============================================================

    def test_prevent_borrowing_when_pending_payment_exists(self):
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            borrow_date="2024-01-01",
            expected_return_date="2030-01-01"
        )

        Payment.objects.create(
            borrowing=borrowing,
            type=Payment.Type.PAYMENT,
            status=Payment.Status.PENDING,
            money_to_pay=Decimal("10.00")
        )

        self.client.force_authenticate(self.user)

        response = self.client.post(
            self.url,
            {
                "book": self.book.id,
                "expected_return_date": "2030-01-01"
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Borrowing.objects.count(), 1)

    # ============================================================
    # UNAUTHENTICATED
    # ============================================================

    def test_unauthenticated_user_cannot_borrow(self):
        response = self.client.post(
            self.url,
            {
                "book": self.book.id,
                "expected_return_date": "2030-01-01"
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)