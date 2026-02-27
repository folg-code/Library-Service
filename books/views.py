from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.viewsets import ModelViewSet

from .models import Book
from .serializers import BookReadSerializer, BookWriteSerializer
from .permissions import IsAdminOrReadOnly

@extend_schema_view(
    list=extend_schema(
        summary="List books",
        description="Retrieve a list of all available books.",
        responses=BookReadSerializer(many=True),
    ),
    retrieve=extend_schema(
        summary="Retrieve book",
        description="Retrieve detailed information about a specific book.",
        responses=BookReadSerializer,
    ),
    create=extend_schema(
        summary="Create book",
        description="Create a new book (Admin only).",
        request=BookWriteSerializer,
        responses=BookReadSerializer,
    ),
    update=extend_schema(
        summary="Update book",
        description="Fully update a book (Admin only).",
        request=BookWriteSerializer,
        responses=BookReadSerializer,
    ),
    partial_update=extend_schema(
        summary="Partially update book",
        description="Partially update book fields including inventory (Admin only).",
        request=BookWriteSerializer,
        responses=BookReadSerializer,
    ),
    destroy=extend_schema(
        summary="Delete book",
        description="Delete a book (Admin only).",
        responses={204: None},
    ),
)
class BookViewSet(ModelViewSet):
    queryset = Book.objects.all()
    permission_classes = [IsAdminOrReadOnly]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return BookReadSerializer
        return BookWriteSerializer
