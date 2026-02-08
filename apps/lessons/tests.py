from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.courses.models import Course
from .models import Lesson


class LessonModelTests(TestCase):
    def test_create_lesson(self) -> None:
        user_model = get_user_model()
        user = user_model.objects.create_user(
            email="lesson-test@example.com",
            username="lessontest",
            password="strong-password-123",
        )
        course = Course.objects.create(
            title="Course A",
            description="Desc",
        )

        lesson = Lesson.objects.create(
            title="Intro",
            content="Welcome",
            course=course,
            user=user,
            video_provider="youtube",
            youtube_url="https://youtu.be/example",
        )

        self.assertEqual(lesson.user_id, user.id)
        self.assertEqual(lesson.course_id, course.id)
        self.assertEqual(lesson.title, "Intro")


class LessonAPITests(TestCase):
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

        self.course = Course.objects.create(title="Course 1", description="Desc")

        self.client = APIClient()
        self.lesson_data = {
            "title": "Lesson 1",
            "content": "Content here",
            "course": self.course.id,
            "user": self.admin.id,
        }

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    # --- Admin CRUD ---
    def test_admin_create_lesson(self):
        self._auth(self.admin)
        res = self.client.post("/lessons/", self.lesson_data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["title"], "Lesson 1")

    def test_admin_list_lessons(self):
        Lesson.objects.create(
            title="L1", content="c", course=self.course, user=self.admin
        )
        self._auth(self.admin)
        res = self.client.get("/lessons/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(len(res.data["results"]), 1)

    def test_admin_get_lesson(self):
        lesson = Lesson.objects.create(
            title="L1", content="c", course=self.course, user=self.admin
        )
        self._auth(self.admin)
        res = self.client.get(f"/lessons/{lesson.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "L1")

    def test_admin_update_lesson(self):
        lesson = Lesson.objects.create(
            title="Old", content="c", course=self.course, user=self.admin
        )
        self._auth(self.admin)
        res = self.client.put(
            f"/lessons/{lesson.id}/",
            {"title": "New", "content": "c", "course": self.course.id, "user": self.admin.id},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "New")

    def test_admin_patch_lesson(self):
        lesson = Lesson.objects.create(
            title="Old", content="c", course=self.course, user=self.admin
        )
        self._auth(self.admin)
        res = self.client.patch(f"/lessons/{lesson.id}/", {"title": "Patched"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "Patched")

    def test_admin_delete_lesson(self):
        lesson = Lesson.objects.create(
            title="Del", content="c", course=self.course, user=self.admin
        )
        self._auth(self.admin)
        res = self.client.delete(f"/lessons/{lesson.id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Lesson.objects.filter(id=lesson.id).exists())

    # --- Student read-only ---
    def test_student_can_list_lessons(self):
        Lesson.objects.create(
            title="L1", content="c", course=self.course, user=self.admin
        )
        self._auth(self.student)
        res = self.client.get("/lessons/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_student_can_get_lesson(self):
        lesson = Lesson.objects.create(
            title="L1", content="c", course=self.course, user=self.admin
        )
        self._auth(self.student)
        res = self.client.get(f"/lessons/{lesson.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_student_cannot_create_lesson(self):
        self._auth(self.student)
        res = self.client.post("/lessons/", self.lesson_data)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_update_lesson(self):
        lesson = Lesson.objects.create(
            title="L1", content="c", course=self.course, user=self.admin
        )
        self._auth(self.student)
        res = self.client.put(
            f"/lessons/{lesson.id}/",
            {"title": "X", "content": "c", "course": self.course.id, "user": self.admin.id},
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_delete_lesson(self):
        lesson = Lesson.objects.create(
            title="L1", content="c", course=self.course, user=self.admin
        )
        self._auth(self.student)
        res = self.client.delete(f"/lessons/{lesson.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # --- Unauthenticated ---
    def test_unauthenticated_cannot_access(self):
        res = self.client.get("/lessons/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- 404 ---
    def test_get_nonexistent_lesson(self):
        self._auth(self.admin)
        res = self.client.get("/lessons/9999/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
