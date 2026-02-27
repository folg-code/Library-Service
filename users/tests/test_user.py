from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class UserRegistrationTests(APITestCase):
    def test_user_can_register(self):
        url = reverse("users-list")

        payload = {
            "email": "test@example.com",
            "password": "strongpassword123",
            "first_name": "John",
            "last_name": "Doe",
        }

        response = self.client.post(url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.first().email, payload["email"])


class UserAuthTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="auth@example.com",
            password="strongpassword123",
            first_name="Auth",
            last_name="User",
        )

    def test_user_can_obtain_token(self):
        url = reverse("token-obtain")

        payload = {
            "email": "auth@example.com",
            "password": "strongpassword123",
        }

        response = self.client.post(url, payload)

        print(response.status_code)
        print(response.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_user_can_access_me(self):
        token_url = reverse("token-obtain")

        token_response = self.client.post(token_url, {
            "email": "auth@example.com",
            "password": "strongpassword123",
        })

        access = token_response.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Authorize {access}")

        url = reverse("users-me")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "auth@example.com")

    def test_me_requires_authentication(self):
        url = reverse("users-me")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
