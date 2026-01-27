from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

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


class PaymentSuccessView(APIView):
    def get(self, request):
        session_id = request.query_params.get("session_id")

        payment = Payment.objects.filter(
            session_id=session_id
        ).first()

        if not payment:
            return Response(
                {"detail": "Payment not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        payment.status = Payment.Status.PAID
        payment.save()

        return Response({"detail": "Payment successful"})


class PaymentCancelView(APIView):
    def get(self, request):
        return Response(
            {"detail": "Payment was cancelled"},
            status=status.HTTP_200_OK,
        )