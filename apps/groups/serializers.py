from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.courses.models import Course
from apps.courses.serializers import CourseSerializer
from apps.users.serializers import UserSerializer

from .models import Group

User = get_user_model()

class GroupListSerializer(serializers.ModelSerializer):
    instructor_name = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
    course_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = (
            "id",
            "name",
            "description",
            "instructor",
            "instructor_name",
            "student_count",
            "course_count",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def get_instructor_name(self, obj):
        if obj.instructor:
            full = f"{obj.instructor.first_name} {obj.instructor.last_name}".strip()
            return full or obj.instructor.username
        return None

    def get_student_count(self, obj):
        return obj.students.count()

    def get_course_count(self, obj):
        return obj.courses.count()

class GroupDetailSerializer(serializers.ModelSerializer):
    instructor_detail = UserSerializer(source="instructor", read_only=True)
    students_detail = UserSerializer(source="students", many=True, read_only=True)
    courses_detail = CourseSerializer(source="courses", many=True, read_only=True)

    instructor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )
    students = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        required=False,
    )
    courses = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = Group
        fields = (
            "id",
            "name",
            "description",
            "instructor",
            "instructor_detail",
            "students",
            "students_detail",
            "courses",
            "courses_detail",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def validate_instructor(self, value):
        if value and value.role != "instructor":
            raise serializers.ValidationError(
                "The assigned user must have the instructor role."
            )
        return value
