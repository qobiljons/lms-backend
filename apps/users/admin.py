from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User, UserProfile

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    ordering = ("username",)
    list_display = ("username", "email", "first_name", "last_name", "role", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    list_filter = ("role", "is_staff", "is_active")

    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2", "role", "is_staff", "is_active"),
        }),
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at")
    search_fields = ("user__email",)
    ordering = ("-created_at",)
