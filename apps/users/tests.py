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

    def test_admin_get_user_by_username(self):
        self._auth(self.admin)
        res = self.client.get(f"/auth/users/{self.student.username}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["username"], "student")
        self.assertIn("profile", res.data)

    def test_get_nonexistent_user(self):
        self._auth(self.admin)
        res = self.client.get("/auth/users/nonexistent/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_cannot_get_user_by_username(self):
        self._auth(self.student)
        res = self.client.get(f"/auth/users/{self.admin.username}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_get_user(self):
        res = self.client.get(f"/auth/users/{self.student.username}/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_update_user_role(self):
        self._auth(self.admin)
        res = self.client.patch(f"/auth/users/{self.student.username}/", {"role": "instructor"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["role"], "instructor")

    def test_admin_update_user_name(self):
        self._auth(self.admin)
        res = self.client.patch(f"/auth/users/{self.student.username}/", {
            "first_name": "Updated", "last_name": "Name"
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["first_name"], "Updated")

    def test_admin_deactivate_user(self):
        self._auth(self.admin)
        res = self.client.patch(f"/auth/users/{self.student.username}/", {"is_active": False})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data["is_active"])

    def test_admin_reactivate_user(self):
        self.student.is_active = False
        self.student.save()
        self._auth(self.admin)
        res = self.client.patch(f"/auth/users/{self.student.username}/", {"is_active": True})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["is_active"])

    def test_admin_update_duplicate_email_rejected(self):
        self._auth(self.admin)
        res = self.client.patch(f"/auth/users/{self.student.username}/", {"email": "admin@test.com"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_update_duplicate_username_rejected(self):
        self._auth(self.admin)
        res = self.client.patch(f"/auth/users/{self.student.username}/", {"username": "admin"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_delete_user(self):
        self._auth(self.admin)
        res = self.client.delete(f"/auth/users/{self.student.username}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        from django.contrib.auth import get_user_model
        self.assertFalse(get_user_model().objects.filter(username="student").exists())

    def test_admin_delete_nonexistent_user(self):
        self._auth(self.admin)
        res = self.client.delete("/auth/users/nonexistent/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_cannot_update_user(self):
        self._auth(self.student)
        res = self.client.patch(f"/auth/users/{self.admin.username}/", {"role": "student"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_delete_user(self):
        self._auth(self.student)
        res = self.client.delete(f"/auth/users/{self.admin.username}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_set_user_password(self):
        self._auth(self.admin)
        res = self.client.post(f"/auth/users/{self.student.username}/set-password/", {
            "new_password": "brandnew123",
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password("brandnew123"))

    def test_admin_set_password_too_short(self):
        self._auth(self.admin)
        res = self.client.post(f"/auth/users/{self.student.username}/set-password/", {
            "new_password": "short",
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_set_password_nonexistent_user(self):
        self._auth(self.admin)
        res = self.client.post("/auth/users/nonexistent/set-password/", {
            "new_password": "brandnew123",
        })
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_cannot_set_user_password(self):
        self._auth(self.student)
        res = self.client.post(f"/auth/users/{self.admin.username}/set-password/", {
            "new_password": "brandnew123",
        })
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

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
        self.assertIn("avatars/", res.data["avatar"])

    def test_avatar_persists_after_upload(self):
        from io import BytesIO
        from PIL import Image
        img = Image.new("RGB", (50, 50), color="green")
        buf = BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        buf.name = "persist.jpg"
        self.client.patch("/auth/me/profile/", {"avatar": buf}, format="multipart")
        res = self.client.get("/auth/me/profile/")
        self.assertIn("avatars/", res.data["avatar"])

    def test_avatar_in_me_response(self):
        from io import BytesIO
        from PIL import Image
        img = Image.new("RGB", (50, 50), color="blue")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        buf.name = "nested.png"
        self.client.patch("/auth/me/profile/", {"avatar": buf}, format="multipart")
        res = self.client.get("/auth/me/")
        self.assertIn("avatars/", res.data["profile"]["avatar"])

    def test_avatar_replace(self):
        from io import BytesIO
        from PIL import Image
        # Upload first
        img1 = Image.new("RGB", (50, 50), color="red")
        buf1 = BytesIO()
        img1.save(buf1, format="PNG")
        buf1.seek(0)
        buf1.name = "first.png"
        res1 = self.client.patch("/auth/me/profile/", {"avatar": buf1}, format="multipart")
        first_url = res1.data["avatar"]
        # Upload second
        img2 = Image.new("RGB", (50, 50), color="green")
        buf2 = BytesIO()
        img2.save(buf2, format="PNG")
        buf2.seek(0)
        buf2.name = "second.png"
        res2 = self.client.patch("/auth/me/profile/", {"avatar": buf2}, format="multipart")
        second_url = res2.data["avatar"]
        self.assertNotEqual(first_url, second_url)
        self.assertIn("avatars/", second_url)

    def test_avatar_clear(self):
        from io import BytesIO
        from PIL import Image
        img = Image.new("RGB", (50, 50), color="red")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        buf.name = "toclear.png"
        self.client.patch("/auth/me/profile/", {"avatar": buf}, format="multipart")
        res = self.client.patch("/auth/me/profile/", {"avatar": ""}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data["avatar"])

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


class DashboardStatsAPITests(TestCase):
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

    def test_admin_get_stats(self):
        from apps.courses.models import Course
        from apps.lessons.models import Lesson
        Course.objects.create(title="C1", description="d")
        Course.objects.create(title="C2", description="d")
        c = Course.objects.first()
        Lesson.objects.create(title="L1", content="c", course=c, user=self.admin)

        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/auth/dashboard/stats/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["users"]["total"], 2)
        self.assertEqual(res.data["users"]["admins"], 1)
        self.assertEqual(res.data["users"]["students"], 1)
        self.assertEqual(res.data["courses"]["total"], 2)
        self.assertEqual(res.data["lessons"]["total"], 1)

    def test_student_cannot_get_stats(self):
        self.client.force_authenticate(user=self.student)
        res = self.client.get("/auth/dashboard/stats/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_get_stats(self):
        res = self.client.get("/auth/dashboard/stats/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
