from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiExample, OpenApiResponse
from rest_framework import viewsets, permissions, mixins
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    UserRegisterSerializer,
    UserReadSerializer,
    EmailTokenObtainPairSerializer
)

User = get_user_model()


@extend_schema_view(
    create=extend_schema(
        summary="Register new user",
        description=(
            "Create a new user account.\n\n"
            "Rules:\n"
            "- Email must be unique\n"
            "- Password must be at least 8 characters\n"
            "- Password is write-only\n"
        ),
        examples=[
            OpenApiExample(
                "Registration example",
                value={
                    "email": "user@example.com",
                    "password": "strongpassword123",
                    "first_name": "John",
                    "last_name": "Doe",
                },
            )
        ],
        responses={
            201: UserReadSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    ),
)
class UserViewSet(
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    queryset = User.objects.all()

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return UserRegisterSerializer
        return UserReadSerializer

    @extend_schema(
        summary="Get or update current user",
        description=(
                "Endpoint for authenticated user.\n\n"
                "GET → return current user profile\n"
                "PUT/PATCH → update current user profile\n\n"
                "Authentication required."
        ),
        request=UserReadSerializer,
        responses={200: UserReadSerializer},
    )
    @action(methods=["get", "put", "patch"], detail=False)
    @action(methods=["get", "put", "patch"], detail=False)
    def me(self, request):
        if request.method == "GET":
            serializer = UserReadSerializer(request.user)
            return Response(serializer.data)

        serializer = UserReadSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@extend_schema(
    summary="Obtain JWT token pair",
    description=(
        "Authenticate user using email and password.\n\n"
        "Returns access and refresh tokens.\n"
        "Uses email instead of username."
    ),
    examples=[
        OpenApiExample(
            "Login example",
            value={
                "email": "user@example.com",
                "password": "strongpassword123",
            },
        )
    ],
    responses={
        200: OpenApiResponse(
            description="JWT token pair",
            response={
                "type": "object",
                "properties": {
                    "refresh": {"type": "string"},
                    "access": {"type": "string"},
                },
            },
        ),
        401: OpenApiResponse(description="Invalid credentials"),
    },
)
class PublicEmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


@extend_schema(
    summary="Refresh JWT access token",
    description=(
        "Generate new access token using refresh token.\n\n"
        "Public endpoint."
    ),
    examples=[
        OpenApiExample(
            "Refresh example",
            value={
                "refresh": "your_refresh_token_here"
            },
        )
    ],
    responses={
        200: OpenApiResponse(
            description="New access token",
            response={
                "type": "object",
                "properties": {
                    "access": {"type": "string"},
                },
            },
        ),
        401: OpenApiResponse(description="Invalid refresh token"),
    },
)
class PublicTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []
