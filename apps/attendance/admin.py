from django.contrib import admin

from .models import AttendanceRecord, AttendanceSession


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0
    autocomplete_fields = ("student",)


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "group",
        "course",
        "session_date",
        "taken_by",
        "created_at",
    )
    search_fields = ("group__name", "course__title", "taken_by__username", "note")
    list_filter = ("session_date", "group", "course")
    ordering = ("-session_date", "-created_at")
    autocomplete_fields = ("group", "course", "taken_by")
    inlines = [AttendanceRecordInline]


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "student", "status", "marked_at")
    search_fields = ("student__username", "session__group__name", "session__course__title")
    list_filter = ("status", "session__group", "session__course", "session__session_date")
    ordering = ("-session__session_date", "student__username")
    autocomplete_fields = ("session", "student")
