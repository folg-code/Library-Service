from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    PublicEmailTokenObtainPairView,
    PublicTokenRefreshView,
)

router = DefaultRouter()
router.register("", UserViewSet, basename="users")

urlpatterns = [
    path("token/", PublicEmailTokenObtainPairView.as_view(), name="token-obtain"),
    path("token/refresh/", PublicTokenRefreshView.as_view(), name="token-refresh"),
] + router.urls