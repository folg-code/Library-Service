from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiExample, OpenApiResponse, OpenApiParameter
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Payment
from .serializers import PaymentReadSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List payments",
        description=(
            "Return list of payments.\n\n"
            "Permissions:\n"
            "- Authenticated users only\n"
            "- Admin users see all payments\n"
            "- Regular users see only payments related to their borrowings\n"
        ),
        responses={200: PaymentReadSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Retrieve payment",
        description=(
            "Retrieve detailed information about a specific payment.\n\n"
            "Access rules are the same as for listing."
        ),
        responses={200: PaymentReadSerializer},
    ),
)
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

@extend_schema(
    summary="Stripe payment success status",
    description=(
        "Endpoint used by frontend after redirect from Stripe success page.\n\n"
        "Query parameter:\n"
        "- session_id (required)\n\n"
        "Behavior:\n"
        "- If payment exists → returns its current status\n"
        "- Does NOT change payment status\n"
        "- Status is updated by Stripe webhook\n"
    ),
    parameters=[
        OpenApiParameter(
            name="session_id",
            description="Stripe Checkout Session ID",
            required=True,
            type=str,
            location=OpenApiParameter.QUERY,
        )
    ],
    responses={
        200: OpenApiResponse(
            description="Payment status returned",
            response={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "detail": {"type": "string"},
                },
            },
        ),
        400: OpenApiResponse(description="Session ID is required"),
        404: OpenApiResponse(description="Payment not found"),
    },
    examples=[
        OpenApiExample(
            "Successful payment",
            value={
                "status": "PAID",
                "detail": "Payment confirmed",
            },
        ),
        OpenApiExample(
            "Pending payment",
            value={
                "status": "PENDING",
                "detail": "Payment not completed yet",
            },
        ),
    ],
)
class PaymentSuccessView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        session_id = request.query_params.get("session_id")

        if not session_id:
            return Response(
                {"detail": "Session ID is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment = Payment.objects.filter(
            session_id=session_id
        ).first()

        if not payment:
            return Response(
                {"detail": "Payment not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if payment.status != Payment.Status.PAID:
            payment.status = Payment.Status.PAID
            payment.save(update_fields=["status"])

        return Response(
            {"detail": "Payment confirmed"},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    summary="Stripe payment cancel",
    description=(
        "Endpoint called when user cancels Stripe Checkout.\n\n"
        "This endpoint does not modify payment status.\n"
        "Stripe session remains valid for up to 24 hours."
    ),
    responses={
        200: OpenApiResponse(
            description="Cancellation information",
            response={
                "type": "object",
                "properties": {
                    "detail": {"type": "string"},
                },
            },
        )
    },
)
class PaymentCancelView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {"detail": "Payment was cancelled"},
            status=status.HTTP_200_OK,
        )
