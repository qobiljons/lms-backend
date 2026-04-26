from django.contrib import admin

from .models import Group

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "instructor", "created_at")
    search_fields = ("name", "description")
    ordering = ("-created_at",)
    filter_horizontal = ("students", "courses")
