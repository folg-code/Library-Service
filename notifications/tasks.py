from celery import shared_task
from django.utils.timezone import now

from borrowings.models import Borrowing
from payments.models import Payment
from .services import send_telegram_message


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def notify(text: str) -> None:
    send_telegram_message(text)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
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

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
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

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def notify_borrowing_returned(borrowing_id: int) -> None:
    borrowing = (
        Borrowing.objects
        .select_related("book", "user")
        .filter(id=borrowing_id)
        .first()
    )

    if not borrowing:
        return

    message = (
        "🔄 <b>Borrowing returned</b>\n"
        f"User: {borrowing.user.email}\n"
        f"Book: {borrowing.book.title}\n"
        f"Returned: {borrowing.actual_return_date}"
    )

    send_telegram_message(message)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def notify_overdue_fine_created(payment_id: int) -> None:
    payment = (
        Payment.objects
        .select_related("borrowing", "borrowing__book", "borrowing__user")
        .filter(id=payment_id)
        .first()
    )

    if not payment:
        return

    message = (
        "⚠️ <b>Overdue fine created</b>\n"
        f"User: {payment.borrowing.user.email}\n"
        f"Book: {payment.borrowing.book.title}\n"
        f"Fine: ${payment.money_to_pay}"
    )

    send_telegram_message(message)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def check_overdue_borrowings(self) -> None:
    today = now().date()

    overdue = (
        Borrowing.objects
        .select_related("book", "user")
        .filter(
            expected_return_date__lt=today,
            actual_return_date__isnull=True,
        )
    )

    if not overdue.exists():
        return

    lines = []
    for borrowing in overdue:
        lines.append(
            f"- {borrowing.user.email} | "
            f"{borrowing.book.title} | "
            f"Due: {borrowing.expected_return_date}"
        )

    message = (
        "⏰ <b>Overdue borrowings detected</b>\n\n"
        + "\n".join(lines)
    )

    send_telegram_message(message)