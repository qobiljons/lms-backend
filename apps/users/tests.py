from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import UserProfile


class UserProfileSignalTests(TestCase):
    def test_profile_created_on_user_creation(self) -> None:
        user_model = get_user_model()
        user = user_model.objects.create_user(
            email="signal-test@example.com",
            username="signaltest",
            password="strong-password-123",
        )

        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        # Ensure the related_name works as expected.
        self.assertEqual(user.profile.user_id, user.id)


class AdminCreateUserAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            email="admin@test.com", username="admin", password="pass12345"
        )
        self.admin.role = "admin"
        self.admin.save()

        self.student = User.objects.create_user(
            email="student@test.com", username="student", password="pass12345"
        )

        self.client = APIClient()

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def test_admin_create_student(self):
        self._auth(self.admin)
        res = self.client.post("/auth/users/create/", {
            "email": "new@test.com",
            "username": "newuser",
            "password": "pass12345",
            "role": "student",
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["role"], "student")

    def test_admin_create_instructor(self):
        self._auth(self.admin)
        res = self.client.post("/auth/users/create/", {
            "email": "inst@test.com",
            "username": "instructor1",
            "password": "pass12345",
            "role": "instructor",
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["role"], "instructor")

    def test_admin_create_admin(self):
        self._auth(self.admin)
        res = self.client.post("/auth/users/create/", {
            "email": "admin2@test.com",
            "username": "admin2",
            "password": "pass12345",
            "role": "admin",
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["role"], "admin")

    def test_admin_create_default_role_is_student(self):
        self._auth(self.admin)
        res = self.client.post("/auth/users/create/", {
            "email": "def@test.com",
            "username": "defuser",
            "password": "pass12345",
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["role"], "student")

    def test_admin_create_duplicate_email_rejected(self):
        self._auth(self.admin)
        res = self.client.post("/auth/users/create/", {
            "email": "admin@test.com",
            "username": "another",
            "password": "pass12345",
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_create_duplicate_username_rejected(self):
        self._auth(self.admin)
        res = self.client.post("/auth/users/create/", {
            "email": "unique@test.com",
            "username": "admin",
            "password": "pass12345",
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_cannot_create_user(self):
        self._auth(self.student)
        res = self.client.post("/auth/users/create/", {
            "email": "x@test.com",
            "username": "xuser",
            "password": "pass12345",
        })
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_create_user(self):
        res = self.client.post("/auth/users/create/", {
            "email": "x@test.com",
            "username": "xuser",
            "password": "pass12345",
        })
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class MeAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="me@test.com", username="meuser", password="pass12345",
            first_name="Old", last_name="Name",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_me(self):
        res = self.client.get("/auth/me/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["username"], "meuser")
        self.assertIn("profile", res.data)

    def test_patch_me_name(self):
        res = self.client.patch("/auth/me/", {"first_name": "New", "last_name": "User"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["first_name"], "New")
        self.assertEqual(res.data["last_name"], "User")

    def test_patch_me_email(self):
        res = self.client.patch("/auth/me/", {"email": "updated@test.com"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], "updated@test.com")

    def test_patch_me_username(self):
        res = self.client.patch("/auth/me/", {"username": "newusername"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["username"], "newusername")

    def test_patch_me_duplicate_email_rejected(self):
        User = get_user_model()
        User.objects.create_user(email="taken@test.com", username="other", password="pass12345")
        res = self.client.patch("/auth/me/", {"email": "taken@test.com"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_me_duplicate_username_rejected(self):
        User = get_user_model()
        User.objects.create_user(email="other@test.com", username="taken", password="pass12345")
        res = self.client.patch("/auth/me/", {"username": "taken"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_cannot_access_me(self):
        self.client.force_authenticate(user=None)
        res = self.client.get("/auth/me/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class ProfileAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="prof@test.com", username="profuser", password="pass12345"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_profile(self):
        res = self.client.get("/auth/me/profile/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("phone", res.data)
        self.assertIn("bio", res.data)
        self.assertIn("avatar", res.data)

    def test_patch_profile_phone(self):
        res = self.client.patch("/auth/me/profile/", {"phone": "+1234567890"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["phone"], "+1234567890")

    def test_patch_profile_bio(self):
        res = self.client.patch("/auth/me/profile/", {"bio": "Hello world"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["bio"], "Hello world")

    def test_patch_profile_avatar(self):
        from io import BytesIO
        from PIL import Image
        img = Image.new("RGB", (100, 100), color="red")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        buf.name = "avatar.png"
        res = self.client.patch("/auth/me/profile/", {"avatar": buf}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(res.data["avatar"])

    def test_unauthenticated_cannot_access_profile(self):
        self.client.force_authenticate(user=None)
        res = self.client.get("/auth/me/profile/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class ChangePasswordAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="pw@test.com", username="pwuser", password="oldpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_change_password_success(self):
        res = self.client.post("/auth/me/change-password/", {
            "old_password": "oldpass123",
            "new_password": "newpass123",
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass123"))

    def test_change_password_wrong_old(self):
        res = self.client.post("/auth/me/change-password/", {
            "old_password": "wrongpass",
            "new_password": "newpass123",
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_too_short(self):
        res = self.client.post("/auth/me/change-password/", {
            "old_password": "oldpass123",
            "new_password": "short",
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_cannot_change_password(self):
        self.client.force_authenticate(user=None)
        res = self.client.post("/auth/me/change-password/", {
            "old_password": "oldpass123",
            "new_password": "newpass123",
        })
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
