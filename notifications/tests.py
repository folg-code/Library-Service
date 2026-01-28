from celery import shared_task
from .services import send_telegram_message


@shared_task
def notify(text: str) -> None:
    send_telegram_message(text)