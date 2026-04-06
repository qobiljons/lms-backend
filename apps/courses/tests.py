from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.groups.models import Group
from apps.payments.models import CoursePurchase

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
        self.instructor = User.objects.create_user(
            email="instructor@test.com", username="instructor", password="pass12345"
        )
        self.instructor.role = "instructor"
        self.instructor.save()

        self.client = APIClient()
        self.course_data = {"title": "Django 101", "description": "Learn Django"}

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def _auth_jwt(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

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
        assigned = Course.objects.create(title="C1", description="d")
        Course.objects.create(title="C2", description="d")
        group = Group.objects.create(name="G1")
        group.students.add(self.student)
        group.courses.add(assigned)
        self._auth(self.student)
        res = self.client.get("/courses/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["slug"], assigned.slug)

    def test_student_jwt_can_list_paid_courses_without_500(self):
        course = Course.objects.create(title="Paid C1", description="d", price=99)
        group = Group.objects.create(name="G2")
        group.students.add(self.student)
        group.courses.add(course)
        self._auth_jwt(self.student)
        res = self.client.get("/courses/?page_size=50")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["is_accessible"], False)
        self.assertEqual(res.data["results"][0]["is_purchased"], False)

    def test_admin_jwt_can_list_paid_courses(self):
        Course.objects.create(title="Paid C1", description="d", price=99)
        self._auth_jwt(self.admin)
        res = self.client.get("/courses/?page_size=50")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["is_accessible"], True)
        self.assertEqual(res.data["results"][0]["is_purchased"], False)

    def test_student_can_get_course(self):
        course = Course.objects.create(title="C1", description="d")
        group = Group.objects.create(name="G3")
        group.students.add(self.student)
        group.courses.add(course)
        self._auth(self.student)
        res = self.client.get(f"/courses/{course.slug}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_student_cannot_get_unassigned_course(self):
        course = Course.objects.create(title="C3", description="d")
        self._auth(self.student)
        res = self.client.get(f"/courses/{course.slug}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data["detail"], "This course is not assigned to your group.")

    def test_student_can_get_paid_course_after_purchase(self):
        course = Course.objects.create(title="C4", description="d", price=99)
        group = Group.objects.create(name="G4")
        group.students.add(self.student)
        group.courses.add(course)
        self._auth(self.student)

        before = self.client.get(f"/courses/{course.slug}/")
        self.assertEqual(before.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(before.data["detail"], "Please make a purchase to see the course content.")

        CoursePurchase.objects.create(user=self.student, course=course, amount=course.price)
        after = self.client.get(f"/courses/{course.slug}/")
        self.assertEqual(after.status_code, status.HTTP_200_OK)

    def test_instructor_can_edit_assigned_course(self):
        course = Course.objects.create(title="Assigned Course", description="d")
        group = Group.objects.create(name="Instructor Group 1", instructor=self.instructor)
        group.courses.add(course)
        self._auth(self.instructor)
        res = self.client.patch(f"/courses/{course.slug}/", {"title": "Assigned Course Updated"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "Assigned Course Updated")

    def test_instructor_can_create_course(self):
        self._auth(self.instructor)
        res = self.client.post("/courses/", {"title": "Instructor New Course", "description": "d"})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["title"], "Instructor New Course")

    def test_instructor_cannot_edit_unassigned_course(self):
        course = Course.objects.create(title="Unassigned Course", description="d")
        self._auth(self.instructor)
        res = self.client.patch(f"/courses/{course.slug}/", {"title": "Try Update"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data["detail"], "This course is not assigned to you.")

    def test_instructor_can_list_only_assigned_courses(self):
        assigned = Course.objects.create(title="Instructor C1", description="d")
        Course.objects.create(title="Instructor C2", description="d")
        group = Group.objects.create(name="Instructor Group 2", instructor=self.instructor)
        group.courses.add(assigned)
        self._auth(self.instructor)
        res = self.client.get("/courses/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["slug"], assigned.slug)

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
