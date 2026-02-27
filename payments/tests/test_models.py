from decimal import Decimal
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import TestCase

from books.models import Book
from borrowings.models import Borrowing
from payments.models import Payment


class PaymentModelTests(TestCase):

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
            daily_fee=Decimal("2.50"),
        )

        self.borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return_date=date.today() + timedelta(days=5),
        )

    def test_create_payment_with_valid_data(self):
        payment = Payment.objects.create(
            borrowing=self.borrowing,
            type=Payment.Type.PAYMENT,
            money_to_pay=Decimal("12.50"),
        )

        self.assertEqual(payment.borrowing, self.borrowing)
        self.assertEqual(payment.type, Payment.Type.PAYMENT)
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(payment.money_to_pay, Decimal("12.50"))
        self.assertIsNone(payment.session_url)
        self.assertIsNone(payment.session_id)

    def test_create_fine_payment(self):
        payment = Payment.objects.create(
            borrowing=self.borrowing,
            type=Payment.Type.FINE,
            money_to_pay=Decimal("5.00"),
        )

        self.assertEqual(payment.type, Payment.Type.FINE)
        self.assertEqual(payment.status, Payment.Status.PENDING)

    def test_money_to_pay_cannot_be_negative(self):
        payment = Payment(
            borrowing=self.borrowing,
            type=Payment.Type.PAYMENT,
            money_to_pay=Decimal("-1.00"),
        )

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_money_to_pay_can_be_zero(self):
        payment = Payment.objects.create(
            borrowing=self.borrowing,
            type=Payment.Type.PAYMENT,
            money_to_pay=Decimal("0.00"),
        )

        self.assertEqual(payment.money_to_pay, Decimal("0.00"))

    def test_session_fields_are_optional(self):
        payment = Payment.objects.create(
            borrowing=self.borrowing,
            type=Payment.Type.PAYMENT,
            money_to_pay=Decimal("10.00"),
        )

        self.assertIsNone(payment.session_url)
        self.assertIsNone(payment.session_id)

    def test_payment_status_can_be_changed_to_paid(self):
        payment = Payment.objects.create(
            borrowing=self.borrowing,
            type=Payment.Type.PAYMENT,
            money_to_pay=Decimal("10.00"),
        )

        payment.status = Payment.Status.PAID
        payment.save()

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PAID)

    def test_borrowing_can_have_multiple_payments(self):
        payment1 = Payment.objects.create(
            borrowing=self.borrowing,
            type=Payment.Type.PAYMENT,
            money_to_pay=Decimal("10.00"),
        )

        payment2 = Payment.objects.create(
            borrowing=self.borrowing,
            type=Payment.Type.FINE,
            money_to_pay=Decimal("5.00"),
        )

        payments = self.borrowing.payments.all()

        self.assertEqual(payments.count(), 2)
        self.assertIn(payment1, payments)
        self.assertIn(payment2, payments)

    def test_created_at_is_set_automatically(self):
        payment = Payment.objects.create(
            borrowing=self.borrowing,
            type=Payment.Type.PAYMENT,
            money_to_pay=Decimal("10.00"),
        )

        self.assertIsNotNone(payment.created_at)

    def test_str_representation(self):
        payment = Payment.objects.create(
            borrowing=self.borrowing,
            type=Payment.Type.PAYMENT,
            money_to_pay=Decimal("10.00"),
        )

        result = str(payment)

        self.assertIn("PAYMENT", result)
        self.assertIn("10.00", result)
        self.assertIn("PENDING", result)
