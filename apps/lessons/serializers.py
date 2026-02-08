from rest_framework import serializers

from .models import Lesson


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = (
            "id",
            "title",
            "content",
            "course",
            "user",
            "video_provider",
            "youtube_url",
            "created_at",
        )
        read_only_fields = ("id", "created_at")
