from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    DirectConversation,
    DirectMessage,
    GroupConversation,
    GroupMessage,
)

User = get_user_model()

class UserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "role")

class DirectMessageSerializer(serializers.ModelSerializer):
    sender_detail = UserMiniSerializer(source="sender", read_only=True)

    class Meta:
        model = DirectMessage
        fields = ("id", "conversation", "sender", "sender_detail", "body", "is_read", "read_at", "created_at")
        read_only_fields = ("id", "conversation", "sender", "created_at", "read_at")

class DirectConversationSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = DirectConversation
        fields = ("id", "other_user", "last_message", "unread_count", "updated_at")

    def get_other_user(self, obj):
        me = self.context["request"].user
        other = obj.user_b if obj.user_a_id == me.id else obj.user_a
        return UserMiniSerializer(other).data

    def get_last_message(self, obj):
        last = obj.messages.order_by("-created_at").first()
        if not last:
            return None
        return DirectMessageSerializer(last).data

    def get_unread_count(self, obj):
        me = self.context["request"].user

        return obj.messages.filter(is_read=False).exclude(sender=me).count()

class GroupMessageSerializer(serializers.ModelSerializer):
    sender_detail = UserMiniSerializer(source="sender", read_only=True)

    class Meta:
        model = GroupMessage
        fields = ("id", "conversation", "sender", "sender_detail", "body", "created_at")
        read_only_fields = ("id", "conversation", "sender", "created_at")

class GroupConversationSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = GroupConversation
        fields = ("id", "group", "group_name", "last_message", "unread_count", "updated_at")

    def get_last_message(self, obj):
        last = obj.messages.order_by("-created_at").first()
        if not last:
            return None
        return GroupMessageSerializer(last).data

    def get_unread_count(self, obj):
        me = self.context["request"].user
        from .models import MessageReadReceipt

        read_message_ids = MessageReadReceipt.objects.filter(
            user=me,
            group_message__conversation=obj
        ).values_list('group_message_id', flat=True)

        return obj.messages.exclude(id__in=read_message_ids).exclude(sender=me).count()
