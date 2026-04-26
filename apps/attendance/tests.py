from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.courses.models import Course
from apps.groups.models import Group

from .models import AttendanceRecord, AttendanceSession

class AttendanceAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            email="admin@attendance.com", username="admin_att", password="pass12345"
        )
        self.admin.role = "admin"
        self.admin.save()

        self.instructor = User.objects.create_user(
            email="inst@attendance.com", username="inst_att", password="pass12345"
        )
        self.instructor.role = "instructor"
        self.instructor.save()

        self.other_instructor = User.objects.create_user(
            email="inst2@attendance.com", username="inst_att2", password="pass12345"
        )
        self.other_instructor.role = "instructor"
        self.other_instructor.save()

        self.student1 = User.objects.create_user(
            email="stud1@attendance.com", username="stud_att_1", password="pass12345"
        )
        self.student2 = User.objects.create_user(
            email="stud2@attendance.com", username="stud_att_2", password="pass12345"
        )

        self.course = Course.objects.create(title="Math", description="Math Course")
        self.group = Group.objects.create(name="Group A", instructor=self.instructor)
        self.group.students.add(self.student1, self.student2)
        self.group.courses.add(self.course)

        self.client = APIClient()

    def test_instructor_can_create_attendance_with_auto_absent(self):
        self.client.force_authenticate(user=self.instructor)
        response = self.client.post(
            "/attendance/",
            {
                "group": self.group.id,
                "course": self.course.id,
                "session_date": str(date.today()),
                "records": [
                    {"student": self.student1.id, "status": "attended"},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = AttendanceSession.objects.get(id=response.data["id"])
        self.assertEqual(session.records.count(), 2)
        self.assertTrue(
            session.records.filter(student=self.student2, status="absent").exists()
        )

    def test_instructor_cannot_take_other_instructor_group_attendance(self):
        other_group = Group.objects.create(name="Group B", instructor=self.other_instructor)
        other_group.students.add(self.student1)
        other_group.courses.add(self.course)

        self.client.force_authenticate(user=self.instructor)
        response = self.client.post(
            "/attendance/",
            {
                "group": other_group.id,
                "course": self.course.id,
                "session_date": str(date.today()),
                "records": [{"student": self.student1.id, "status": "attended"}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_can_view_only_own_attendance_summary(self):
        session = AttendanceSession.objects.create(
            group=self.group,
            course=self.course,
            taken_by=self.instructor,
            session_date=date.today(),
        )
        AttendanceRecord.objects.create(
            session=session, student=self.student1, status="attended_online"
        )
        AttendanceRecord.objects.create(
            session=session, student=self.student2, status="absent"
        )

        self.client.force_authenticate(user=self.student1)
        response = self.client.get("/attendance/my/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["summary"]["total_records"], 1)
        self.assertEqual(
            response.data["summary"]["status_breakdown"]["attended_online"], 1
        )

    def test_admin_can_view_attendance_overview(self):
        session = AttendanceSession.objects.create(
            group=self.group,
            course=self.course,
            taken_by=self.instructor,
            session_date=date.today(),
        )
        AttendanceRecord.objects.create(
            session=session, student=self.student1, status="attended"
        )
        AttendanceRecord.objects.create(
            session=session, student=self.student2, status="absent"
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/attendance/overview/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_sessions"], 1)
        self.assertEqual(response.data["status_breakdown"]["attended"], 1)
        self.assertEqual(response.data["status_breakdown"]["absent"], 1)
