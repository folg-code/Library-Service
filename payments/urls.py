from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import PaymentsViewSet, PaymentSuccessView, PaymentCancelView
from .webhooks import StripeWebhookView

router = DefaultRouter()
router.register("", PaymentsViewSet, basename="payments")

urlpatterns = [
    path("success/", PaymentSuccessView.as_view(), name="payment-success"),
    path("cancel/", PaymentCancelView.as_view(), name="payment-cancel"),
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
] + router.urls