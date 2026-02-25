from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from users.models import User
from books.models import Book
from borrowings.models import Borrowing
from payments.models import Payment


class StripeWebhookTests(TestCase):

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

        self.borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            borrow_date="2024-01-01",
            expected_return_date="2030-01-01",
        )

        self.payment = Payment.objects.create(
            borrowing=self.borrowing,
            type=Payment.Type.PAYMENT,
            status=Payment.Status.PENDING,
            session_id="sess_123",
            money_to_pay=Decimal("10.00"),
        )

        self.url = reverse("stripe-webhook")

    # ===============================
    # SUCCESS FLOW
    # ===============================

    @patch("payments.webhooks.notify_payment_completed.delay")
    @patch("stripe.Webhook.construct_event")
    def test_checkout_completed_marks_paid(
        self,
        mock_construct,
        mock_notify,
    ):
        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {"id": "sess_123"}
            }
        }

        response = self.client.post(
            self.url,
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )

        self.assertEqual(response.status_code, 200)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PAID)

        mock_notify.assert_called_once_with(self.payment.id)

    # ===============================
    # IDEMPOTENCY
    # ===============================

    @patch("payments.webhooks.notify_payment_completed.delay")
    @patch("stripe.Webhook.construct_event")
    def test_idempotent_when_already_paid(
        self,
        mock_construct,
        mock_notify,
    ):
        self.payment.status = Payment.Status.PAID
        self.payment.save()

        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {"id": "sess_123"}
            }
        }

        response = self.client.post(
            self.url,
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )

        self.assertEqual(response.status_code, 200)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PAID)

        mock_notify.assert_not_called()

    # ===============================
    # PAYMENT NOT FOUND
    # ===============================

    @patch("payments.webhooks.notify_payment_completed.delay")
    @patch("stripe.Webhook.construct_event")
    def test_checkout_completed_payment_not_found(
        self,
        mock_construct,
        mock_notify,
    ):
        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {"id": "unknown_session"}
            }
        }

        response = self.client.post(
            self.url,
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )

        self.assertEqual(response.status_code, 200)
        mock_notify.assert_not_called()

    # ===============================
    # INVALID SIGNATURE
    # ===============================

    @patch("stripe.Webhook.construct_event")
    def test_invalid_signature_returns_400(self, mock_construct):
        mock_construct.side_effect = ValueError("Invalid payload")

        response = self.client.post(
            self.url,
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="bad_sig",
        )

        self.assertEqual(response.status_code, 400)

    # ===============================
    # UNHANDLED EVENT TYPE
    # ===============================

    @patch("stripe.Webhook.construct_event")
    def test_unhandled_event_type_returns_200(self, mock_construct):
        mock_construct.return_value = {
            "type": "customer.created",
            "data": {"object": {}}
        }

        response = self.client.post(
            self.url,
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )

        self.assertEqual(response.status_code, 200)