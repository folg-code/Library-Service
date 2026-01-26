from django.test import TestCase
from django.contrib.auth import get_user_model


class UserModelTests(TestCase):

    def test_create_user_with_email(self):
        User = get_user_model()
        user = User.objects.create_user(
            email="test@example.com",
            password="password123",
            first_name="Test",
            last_name="User",
        )

        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("password123"))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)