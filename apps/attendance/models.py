from django.conf import settings
from django.db import models

class AttendanceSession(models.Model):
    group = models.ForeignKey(
        "groups.Group",
        on_delete=models.CASCADE,
        related_name="attendance_sessions",
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.SET_NULL,
        related_name="attendance_sessions",
        null=True,
        blank=True,
    )
    taken_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="attendance_taken_sessions",
        null=True,
    )
    session_date = models.DateField()
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "attendance_sessions"
        ordering = ["-session_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["group", "course", "session_date"],
                name="unique_attendance_group_course_session_date",
            ),
        ]

    def __str__(self) -> str:
        course_text = self.course.title if self.course else "General"
        return f"{self.group.name} - {course_text} ({self.session_date})"

class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        ATTENDED = "attended", "Attended"
        ATTENDED_ONLINE = "attended_online", "Attended Online"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"
        EXCUSED = "excused", "Excused"

    session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name="records",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ABSENT)
    note = models.CharField(max_length=255, blank=True)
    marked_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "attendance_records"
        ordering = ["student__username"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "student"],
                name="unique_attendance_session_student",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student.username} - {self.status}"
