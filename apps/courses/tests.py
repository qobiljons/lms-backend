from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import Course


class CourseModelTests(TestCase):
    def test_create_course(self) -> None:
        course = Course.objects.create(
            title="Python 101",
            description="Intro course",
        )
        self.assertEqual(course.title, "Python 101")

    def test_unique_title(self) -> None:
        Course.objects.create(title="Unique", description="First")
        with self.assertRaises(Exception):
            Course.objects.create(title="Unique", description="Second")


class CourseAPITests(TestCase):
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
        self.course_data = {"title": "Django 101", "description": "Learn Django"}

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    # --- Admin CRUD ---
    def test_admin_create_course(self):
        self._auth(self.admin)
        res = self.client.post("/courses/", self.course_data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["title"], "Django 101")

    def test_admin_list_courses(self):
        Course.objects.create(title="C1", description="d")
        self._auth(self.admin)
        res = self.client.get("/courses/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(len(res.data["results"]), 1)

    def test_admin_get_course(self):
        course = Course.objects.create(title="C1", description="d")
        self._auth(self.admin)
        res = self.client.get(f"/courses/{course.slug}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "C1")

    def test_admin_update_course(self):
        course = Course.objects.create(title="Old", description="d")
        self._auth(self.admin)
        res = self.client.put(f"/courses/{course.slug}/", {"title": "New", "description": "d"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "New")

    def test_admin_patch_course(self):
        course = Course.objects.create(title="Old", description="d")
        self._auth(self.admin)
        res = self.client.patch(f"/courses/{course.slug}/", {"title": "Patched"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "Patched")

    def test_admin_delete_course(self):
        course = Course.objects.create(title="Del", description="d")
        self._auth(self.admin)
        res = self.client.delete(f"/courses/{course.slug}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Course.objects.filter(id=course.id).exists())

    # --- Student read-only ---
    def test_student_can_list_courses(self):
        Course.objects.create(title="C1", description="d")
        self._auth(self.student)
        res = self.client.get("/courses/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_student_can_get_course(self):
        course = Course.objects.create(title="C1", description="d")
        self._auth(self.student)
        res = self.client.get(f"/courses/{course.slug}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_student_cannot_create_course(self):
        self._auth(self.student)
        res = self.client.post("/courses/", self.course_data)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_update_course(self):
        course = Course.objects.create(title="C1", description="d")
        self._auth(self.student)
        res = self.client.put(f"/courses/{course.slug}/", {"title": "X", "description": "d"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_delete_course(self):
        course = Course.objects.create(title="C1", description="d")
        self._auth(self.student)
        res = self.client.delete(f"/courses/{course.slug}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # --- Unauthenticated ---
    def test_unauthenticated_cannot_access(self):
        res = self.client.get("/courses/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- 404 ---
    def test_get_nonexistent_course(self):
        self._auth(self.admin)
        res = self.client.get("/courses/9999/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
