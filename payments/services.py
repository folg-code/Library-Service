import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_checkout_session(*, borrowing, amount):
    """
    Create Stripe Checkout Session for a borrowing payment.
    Amount must be provided in cents.
    """
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Borrowing #{borrowing.id}",
                    },
                    "unit_amount": amount,
                },
                "quantity": 1,
            }
        ],
        success_url=settings.STRIPE_SUCCESS_URL + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=settings.STRIPE_CANCEL_URL,
    )

    return session