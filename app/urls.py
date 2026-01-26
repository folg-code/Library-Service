from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),

    # schema & docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),

    # apps (na razie puste)
    path("api/books/", include("books.urls")),
    path("api/users/", include("users.urls")),
    path("api/borrowings/", include("borrowings.urls")),
    path("api/payments/", include("payments.urls")),
]
