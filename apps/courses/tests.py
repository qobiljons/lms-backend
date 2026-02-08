from django.test import TestCase

from .models import Course


class CourseModelTests(TestCase):
    def test_create_course(self) -> None:
        course = Course.objects.create(
            title="Python 101",
            description="Intro course",
        )
        self.assertEqual(course.title, "Python 101")
