from rest_framework.viewsets import ModelViewSet

from .models import Book
from .serializers import BookReadSerializer, BookWriteSerializer
from .permissions import IsAdminOrReadOnly


class BookViewSet(ModelViewSet):
    queryset = Book.objects.all()
    permission_classes = [IsAdminOrReadOnly]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return BookReadSerializer
        return BookWriteSerializer