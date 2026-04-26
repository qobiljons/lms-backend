from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import Homework, HomeworkFile, HomeworkSubmission

User = get_user_model()

class HomeworkSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source="lesson.title", read_only=True)
    lesson_order = serializers.SerializerMethodField()
    lesson_total = serializers.SerializerMethodField()
    course_id = serializers.IntegerField(source="lesson.course_id", read_only=True)
    course_title = serializers.CharField(source="lesson.course.title", read_only=True)
    course_slug = serializers.CharField(source="lesson.course.slug", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)
    submission_status = serializers.SerializerMethodField()

    def get_lesson_order(self, obj):
        if not obj.lesson_id or not obj.lesson.course_id:
            return None
        from apps.lessons.models import Lesson
        ids = list(
            Lesson.objects.filter(course_id=obj.lesson.course_id)
            .order_by("created_at", "id")
            .values_list("id", flat=True)
        )
        try:
            return ids.index(obj.lesson_id) + 1
        except ValueError:
            return None

    def get_lesson_total(self, obj):
        if not obj.lesson_id or not obj.lesson.course_id:
            return None
        from apps.lessons.models import Lesson
        return Lesson.objects.filter(course_id=obj.lesson.course_id).count()

    class Meta:
        model = Homework
        fields = (
            "id",
            "lesson",
            "lesson_title",
            "lesson_order",
            "lesson_total",
            "course_id",
            "course_title",
            "course_slug",
            "title",
            "description",
            "questions",
            "total_points",
            "due_date",
            "created_by",
            "created_by_name",
            "submission_status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by", "created_at", "updated_at")

    def get_submission_status(self, obj):
        """Get current user's submission status for this homework"""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        if request.user.role != "student":
            return None
        try:
            submission = obj.submissions.get(student=request.user)
            return {
                "status": submission.status,
                "score": str(submission.score) if submission.score else None,
                "submitted_at": submission.submitted_at,
            }
        except HomeworkSubmission.DoesNotExist:
            return None

class HomeworkFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeworkFile
        fields = ("id", "file", "filename", "file_type", "file_size", "uploaded_at")
        read_only_fields = ("id", "uploaded_at")

class HomeworkSubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.username", read_only=True)
    student_email = serializers.CharField(source="student.email", read_only=True)
    homework_title = serializers.CharField(source="homework.title", read_only=True)
    graded_by_name = serializers.CharField(source="graded_by.username", read_only=True)
    uploaded_files = HomeworkFileSerializer(many=True, read_only=True)

    class Meta:
        model = HomeworkSubmission
        fields = (
            "id",
            "homework",
            "homework_title",
            "student",
            "student_name",
            "student_email",
            "answers",
            "files",
            "uploaded_files",
            "status",
            "score",
            "feedback",
            "ai_feedback",
            "submitted_at",
            "graded_at",
            "graded_by",
            "graded_by_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "student",
            "submitted_at",
            "graded_at",
            "graded_by",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        if attrs.get("status") == "submitted" and self.instance and not self.instance.submitted_at:
            attrs["submitted_at"] = timezone.now()
        return attrs

class HomeworkSubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeworkSubmission
        fields = ("id", "homework", "answers", "files", "status")
        read_only_fields = ("id",)

    def create(self, validated_data):
        validated_data["student"] = self.context["request"].user
        if validated_data.get("status") == "submitted":
            validated_data["submitted_at"] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("status") == "submitted" and not instance.submitted_at:
            validated_data["submitted_at"] = timezone.now()
        return super().update(instance, validated_data)
