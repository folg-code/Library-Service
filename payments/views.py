from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated

from .models import Payment
from .serializers import PaymentReadSerializer


class PaymentsViewSet(ReadOnlyModelViewSet):
    serializer_class = PaymentReadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Payment.objects.select_related(
            "borrowing",
            "borrowing__user",
        )

        if self.request.user.is_staff:
            return queryset

        return queryset.filter(
            borrowing__user=self.request.user
        )