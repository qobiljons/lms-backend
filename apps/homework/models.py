from django.conf import settings
from django.db import models


class Homework(models.Model):
    """Homework assignment for a lesson"""
    lesson = models.ForeignKey(
        "lessons.Lesson",
        on_delete=models.CASCADE,
        related_name="homework_assignments",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(help_text="Homework instructions")
    questions = models.JSONField(
        default=list,
        help_text="List of questions in format: [{'question': '...', 'points': 10}]"
    )
    total_points = models.IntegerField(default=100)
    due_date = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_homework",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "homework"
        ordering = ["-created_at"]
        unique_together = ("lesson", "title")

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"


class HomeworkSubmission(models.Model):
    """Student's homework submission"""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("graded", "Graded"),
        ("returned", "Returned"),
    ]

    homework = models.ForeignKey(
        Homework,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="homework_submissions",
    )
    answers = models.JSONField(
        default=list,
        help_text="List of answers in format: [{'question_index': 0, 'answer': '...', 'file': 'url'}]"
    )
    files = models.JSONField(
        default=list,
        help_text="List of uploaded file URLs"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Score out of total_points"
    )
    feedback = models.TextField(blank=True, help_text="Instructor feedback")
    ai_feedback = models.JSONField(
        default=dict,
        help_text="AI-generated feedback in format: {'overall': '...', 'per_question': [...]}"
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="graded_homework",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "homework_submissions"
        ordering = ["-created_at"]
        unique_together = ("homework", "student")

    def __str__(self):
        return f"{self.student.username} - {self.homework.title}"


class HomeworkFile(models.Model):
    """File uploaded for homework submission"""

    submission = models.ForeignKey(
        HomeworkSubmission,
        on_delete=models.CASCADE,
        related_name="uploaded_files",
    )
    file = models.FileField(upload_to="homework_files/%Y/%m/%d/")
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    file_size = models.IntegerField(help_text="File size in bytes")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "homework_files"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.submission.student.username} - {self.filename}"
