from django.conf import settings
from django.db import models


class Lesson(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="lessons",
        db_column="course_id",
    )
    # This maps to a BIGINT user_id column and keeps referential integrity.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    video_provider = models.CharField(max_length=50, blank=True, null=True)
    youtube_url = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lessons"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title
