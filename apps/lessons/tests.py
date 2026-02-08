from django.contrib.auth import get_user_model
from django.test import TestCase

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
