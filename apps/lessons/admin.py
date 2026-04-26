from django.contrib import admin

from .models import Lesson

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "course", "user", "video_provider", "created_at")
    search_fields = ("title", "content", "youtube_url")
    list_filter = ("video_provider", "created_at")
    ordering = ("-created_at",)
