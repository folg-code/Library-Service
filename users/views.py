from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .serializers import UserRegisterSerializer, UserReadSerializer

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return UserRegisterSerializer
        return UserReadSerializer

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
