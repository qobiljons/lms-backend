from rest_framework import serializers

from .models import Course


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ("id", "title", "slug", "description", "logo", "created_at")
        read_only_fields = ("id", "slug", "created_at")
