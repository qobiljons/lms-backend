from django.contrib import admin

from .models import Homework, HomeworkFile, HomeworkSubmission


class HomeworkFileInline(admin.TabularInline):
    model = HomeworkFile
    extra = 0
    readonly_fields = ("filename", "file_type", "file_size", "uploaded_at")


@admin.register(Homework)
class HomeworkAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "lesson", "total_points", "due_date", "created_by", "created_at")
    search_fields = ("title", "description", "lesson__title")
    list_filter = ("lesson__course", "created_at", "due_date")
    ordering = ("-created_at",)
    autocomplete_fields = ("lesson", "created_by")


@admin.register(HomeworkSubmission)
class HomeworkSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "homework",
        "student",
        "status",
        "score",
        "submitted_at",
        "graded_at",
        "graded_by",
    )
    search_fields = ("homework__title", "student__username", "student__email")
    list_filter = ("status", "submitted_at", "graded_at")
    ordering = ("-created_at",)
    autocomplete_fields = ("homework", "student", "graded_by")
    inlines = [HomeworkFileInline]


@admin.register(HomeworkFile)
class HomeworkFileAdmin(admin.ModelAdmin):
    list_display = ("id", "submission", "filename", "file_type", "file_size", "uploaded_at")
    search_fields = ("filename", "submission__student__username")
    list_filter = ("file_type", "uploaded_at")
    ordering = ("-uploaded_at",)
    autocomplete_fields = ("submission",)
