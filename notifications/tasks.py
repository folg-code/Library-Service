from celery import shared_task

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