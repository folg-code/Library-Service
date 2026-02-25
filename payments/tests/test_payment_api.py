from decimal import Decimal
from unittest.mock import patch
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from users.models import User
from books.models import Book
from borrowings.models import Borrowing
from payments.models import Payment


class PaymentAPITests(APITestCase):

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
            borrow_date="2024-01-01",
            expected_return_date="2030-01-01"
        )

        self.payment = Payment.objects.create(
            borrowing=self.borrowing,
            type=Payment.Type.PAYMENT,
            status=Payment.Status.PENDING,
            session_id="sess_123",
            money_to_pay=Decimal("10.00"),
        )

    def test_user_sees_only_own_payments(self):
        self.client.force_authenticate(self.user)

        url = reverse("payments-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_success_endpoint_marks_paid(self):
        url = reverse("payment-success") + "?session_id=sess_123"

        response = self.client.get(url)

        print(response.status_code)
        print(response.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PAID)

    @patch("payments.webhooks.notify_payment_completed.delay")
    @patch("stripe.Webhook.construct_event")
    def test_webhook_marks_paid_and_is_idempotent(
            self,
            mock_construct,
            mock_notify,
    ):

        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "sess_123"
                }
            }
        }

        url = reverse("stripe-webhook")

        self.client.post(url, data="{}", content_type="application/json")
        self.client.post(url, data="{}", content_type="application/json")

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PAID)