from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import PaymentsViewSet, PaymentSuccessView, PaymentCancelView

router = DefaultRouter()
router.register("", PaymentsViewSet, basename="payments")

urlpatterns = router.urls + [
    path("success/", PaymentSuccessView.as_view(), name="payment-success"),
    path("cancel/", PaymentCancelView.as_view(), name="payment-cancel"),
]