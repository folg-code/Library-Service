from rest_framework.routers import DefaultRouter
from .views import BorrowingViewSet

router = DefaultRouter()
router.register("", BorrowingViewSet, basename="borrowings")

urlpatterns = router.urls
