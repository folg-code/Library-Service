from celery import shared_task

from borrowings.models import Borrowing
from payments.models import Payment
from .services import send_telegram_message


@shared_task
def notify(text: str) -> None:
    send_telegram_message(text)


@shared_task
def notify_payment_completed(payment_id: int) -> None:
    payment = (
        Payment.objects
        .select_related("borrowing", "borrowing__user")
        .filter(id=payment_id)
        .first()
    )

    if not payment:
        return

    if payment.type == Payment.Type.FINE:
        header = "⚠️ <b>Fine payment completed</b>"
    else:
        header = "💰 <b>Payment completed</b>"

    message = (
        f"{header}\n"
        f"Borrowing ID: {payment.borrowing_id}\n"
        f"User: {payment.borrowing.user.email}\n"
        f"Amount: ${payment.money_to_pay}"
    )

    send_telegram_message(message)

@shared_task
def notify_payment_completed(payment_id: int) -> None:
    payment = (
        Payment.objects
        .select_related("borrowing", "borrowing__user")
        .filter(id=payment_id)
        .first()
    )

    if not payment:
        return

    if payment.type == Payment.Type.FINE:
        header = "⚠️ <b>Fine payment completed</b>"
    else:
        header = "💰 <b>Payment completed</b>"

    message = (
        f"{header}\n"
        f"Borrowing ID: {payment.borrowing_id}\n"
        f"User: {payment.borrowing.user.email}\n"
        f"Amount: ${payment.money_to_pay}"
    )

    send_telegram_message(message)

@shared_task
def notify_borrowing_created(borrowing_id: int) -> None:
    borrowing = (
        Borrowing.objects
        .select_related("book", "user")
        .filter(id=borrowing_id)
        .first()
    )

    if not borrowing:
        return

    message = (
        "📚 <b>New borrowing created</b>\n"
        f"Borrowing ID: {borrowing.id}\n"
        f"User: {borrowing.user.email}\n"
        f"Book: {borrowing.book.title}\n"
        f"Expected return: {borrowing.expected_return_date}"
    )

    send_telegram_message(message)