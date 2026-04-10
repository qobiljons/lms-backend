from django.contrib import admin

from .models import DirectConversation, DirectMessage, GroupConversation, GroupMessage


@admin.register(DirectConversation)
class DirectConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user_a", "user_b", "updated_at")
    search_fields = ("user_a__username", "user_b__username")
    ordering = ("-updated_at",)
    autocomplete_fields = ("user_a", "user_b")


@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "sender", "created_at")
    search_fields = ("sender__username", "body")
    ordering = ("-created_at",)
    autocomplete_fields = ("conversation", "sender")


@admin.register(GroupConversation)
class GroupConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "group", "updated_at")
    search_fields = ("group__name",)
    ordering = ("-updated_at",)
    autocomplete_fields = ("group",)


@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "sender", "created_at")
    search_fields = ("sender__username", "body", "conversation__group__name")
    ordering = ("-created_at",)
    autocomplete_fields = ("conversation", "sender")
