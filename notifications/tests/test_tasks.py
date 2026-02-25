from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from users.models import User
from books.models import Book
from borrowings.models import Borrowing
from payments.models import Payment
from notifications.tasks import (
    notify_borrowing_created,
    notify_borrowing_returned,
    notify_overdue_fine_created,
    notify_payment_completed,
    check_overdue_borrowings,
)


class NotificationTasksTests(TestCase):

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
            borrow_date=date.today(),
            expected_return_date=date.today() + timedelta(days=3),
        )

        self.payment = Payment.objects.create(
            borrowing=self.borrowing,
            type=Payment.Type.PAYMENT,
            status=Payment.Status.PAID,
            money_to_pay=Decimal("10.00"),
        )

    # ===============================
    # Borrowing created
    # ===============================

    @patch("notifications.tasks.send_telegram_message")
    def test_notify_borrowing_created(self, mock_send):
        notify_borrowing_created.run(self.borrowing.id)
        mock_send.assert_called_once()

    @patch("notifications.tasks.send_telegram_message")
    def test_notify_borrowing_created_not_found(self, mock_send):
        notify_borrowing_created(999)
        mock_send.assert_not_called()

    # ===============================
    # Borrowing returned
    # ===============================

    @patch("notifications.tasks.send_telegram_message")
    def test_notify_borrowing_returned(self, mock_send):
        self.borrowing.actual_return_date = date.today()
        self.borrowing.save()

        notify_borrowing_returned.run(self.borrowing.id)
        mock_send.assert_called_once()

    # ===============================
    # Payment completed
    # ===============================

    @patch("notifications.tasks.send_telegram_message")
    def test_notify_payment_completed(self, mock_send):
        notify_payment_completed.run(self.payment.id)
        mock_send.assert_called_once()

    @patch("notifications.tasks.send_telegram_message")
    def test_notify_payment_completed_not_found(self, mock_send):
        notify_payment_completed.run(999)
        mock_send.assert_not_called()

    # ===============================
    # Overdue fine created
    # ===============================

    @patch("notifications.tasks.send_telegram_message")
    def test_notify_overdue_fine_created(self, mock_send):
        fine = Payment.objects.create(
            borrowing=self.borrowing,
            type=Payment.Type.FINE,
            status=Payment.Status.PENDING,
            money_to_pay=Decimal("20.00"),
        )

        notify_overdue_fine_created.run(fine.id)
        mock_send.assert_called_once()

    # ===============================
    # Overdue checker
    # ===============================

    @patch("notifications.tasks.send_telegram_message")
    def test_check_overdue_borrowings_with_overdue(self, mock_send):
        self.borrowing.expected_return_date = date.today() - timedelta(days=2)
        self.borrowing.save()

        check_overdue_borrowings()
        self.assertTrue(mock_send.called)

    @patch("notifications.tasks.send_telegram_message")
    def test_check_overdue_borrowings_no_overdue(self, mock_send):
        check_overdue_borrowings()
        mock_send.assert_not_called()
