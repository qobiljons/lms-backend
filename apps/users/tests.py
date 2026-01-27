from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import UserProfile


class UserProfileSignalTests(TestCase):
    def test_profile_created_on_user_creation(self) -> None:
        user_model = get_user_model()
        user = user_model.objects.create_user(
            email="signal-test@example.com",
            password="strong-password-123",
        )

        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        # Ensure the related_name works as expected.
        self.assertEqual(user.profile.user_id, user.id)
