import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views import View

from .models import Payment


class StripeWebhookView(View):
    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=sig_header,
                secret=settings.STRIPE_WEBHOOK_SECRET,
            )
        except ValueError:
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            return HttpResponse(status=400)

        self.handle_event(event)

        return HttpResponse(status=200)

    def handle_event(self, event):
        event_type = event["type"]

        if event_type == "checkout.session.completed":
            self.handle_checkout_completed(event["data"]["object"])

    def handle_checkout_completed(self, session):
        session_id = session.get("id")

        payment = Payment.objects.filter(
            session_id=session_id
        ).first()

        if not payment:
            return

        payment.status = Payment.Status.PAID
        payment.save(update_fields=["status"])

        notify.delay(
            f"💰 <b>Payment completed</b>\n"
            f"Borrowing ID: {payment.borrowing_id}\n"
            f"Amount: ${payment.money_to_pay}"
        )