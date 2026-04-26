from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, serializers, status
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.groups.models import Group

from .models import DirectConversation, DirectMessage, GroupConversation, GroupMessage, MessageReadReceipt
from .serializers import (
    DirectConversationSerializer,
    DirectMessageSerializer,
    GroupConversationSerializer,
    GroupMessageSerializer,
    UserMiniSerializer,
)

User = get_user_model()

class SendMessageSerializer(serializers.Serializer):
    body = serializers.CharField(allow_blank=False, trim_whitespace=True)

def get_or_create_direct_conversation(user_1, user_2):
    if user_1.id > user_2.id:
        user_1, user_2 = user_2, user_1
    conversation, _ = DirectConversation.objects.get_or_create(
        user_a=user_1,
        user_b=user_2,
    )
    return conversation

def user_can_access_group(user, group: Group):
    if user.role == "admin":
        return True
    if group.instructor_id == user.id:
        return True
    return group.students.filter(pk=user.id).exists()

class DirectConversationListAPIView(generics.ListAPIView):
    serializer_class = DirectConversationSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return DirectConversation.objects.filter(
            Q(user_a=user) | Q(user_b=user)
        ).select_related("user_a", "user_b")

class ReachableUserListAPIView(generics.ListAPIView):
    serializer_class = UserMiniSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (SearchFilter,)
    search_fields = ("username", "first_name", "last_name", "email")

    def get_queryset(self):
        return User.objects.exclude(pk=self.request.user.id).order_by("username")

class DirectMessagesAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def _get_target_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    @swagger_auto_schema(responses={200: DirectMessageSerializer(many=True)})
    def get(self, request, user_id):
        target = self._get_target_user(user_id)
        if target is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        if target.id == request.user.id:
            return Response(
                {"detail": "You cannot start a direct conversation with yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        conversation = get_or_create_direct_conversation(request.user, target)
        messages = conversation.messages.select_related("sender")
        return Response(DirectMessageSerializer(messages, many=True).data)

    @swagger_auto_schema(request_body=SendMessageSerializer, responses={201: DirectMessageSerializer})
    def post(self, request, user_id):
        target = self._get_target_user(user_id)
        if target is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        if target.id == request.user.id:
            return Response(
                {"detail": "You cannot send direct messages to yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = SendMessageSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        conversation = get_or_create_direct_conversation(request.user, target)
        message = DirectMessage.objects.create(
            conversation=conversation,
            sender=request.user,
            body=payload.validated_data["body"],
        )
        conversation.save(update_fields=["updated_at"])

        serialized_data = DirectMessageSerializer(message).data
        pair = sorted([request.user.id, target.id])
        room_name = f"dm_{pair[0]}_{pair[1]}"

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            room_name,
            {
                "type": "chat.message",
                "payload": serialized_data,
            },
        )

        return Response(serialized_data, status=status.HTTP_201_CREATED)

class GroupConversationListAPIView(generics.ListAPIView):
    serializer_class = GroupConversationSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        queryset = GroupConversation.objects.select_related("group")
        if user.role == "admin":
            return queryset
        if user.role == "instructor":
            return queryset.filter(group__instructor=user)
        return queryset.filter(group__students=user).distinct()

class GroupMessagesAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def _get_group(self, group_id):
        try:
            return Group.objects.get(pk=group_id)
        except Group.DoesNotExist:
            return None

    @swagger_auto_schema(responses={200: GroupMessageSerializer(many=True)})
    def get(self, request, group_id):
        group = self._get_group(group_id)
        if group is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        if not user_can_access_group(request.user, group):
            return Response(
                {"detail": "You do not have access to this group chat."},
                status=status.HTTP_403_FORBIDDEN,
            )
        conversation, _ = GroupConversation.objects.get_or_create(group=group)
        messages = conversation.messages.select_related("sender")
        return Response(GroupMessageSerializer(messages, many=True).data)

    @swagger_auto_schema(request_body=SendMessageSerializer, responses={201: GroupMessageSerializer})
    def post(self, request, group_id):
        group = self._get_group(group_id)
        if group is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        if not user_can_access_group(request.user, group):
            return Response(
                {"detail": "You do not have access to this group chat."},
                status=status.HTTP_403_FORBIDDEN,
            )

        payload = SendMessageSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        conversation, _ = GroupConversation.objects.get_or_create(group=group)
        message = GroupMessage.objects.create(
            conversation=conversation,
            sender=request.user,
            body=payload.validated_data["body"],
        )
        conversation.save(update_fields=["updated_at"])

        serialized_data = GroupMessageSerializer(message).data
        room_name = f"group_chat_{group_id}"

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            room_name,
            {
                "type": "chat.message",
                "payload": serialized_data,
            },
        )

        return Response(serialized_data, status=status.HTTP_201_CREATED)

class MarkDirectMessagesReadAPIView(APIView):
    """Mark all messages from a user as read"""
    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(responses={200: "Messages marked as read"})
    def post(self, request, user_id):
        try:
            target = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        conversation = get_or_create_direct_conversation(request.user, target)

        from django.utils import timezone
        updated_count = conversation.messages.filter(
            sender=target,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())

        return Response({"marked_read": updated_count}, status=status.HTTP_200_OK)

class MarkGroupMessagesReadAPIView(APIView):
    """Mark all group messages as read for the current user"""
    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(responses={200: "Messages marked as read"})
    def post(self, request, group_id):
        try:
            group = Group.objects.get(pk=group_id)
        except Group.DoesNotExist:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        if not user_can_access_group(request.user, group):
            return Response(
                {"detail": "You do not have access to this group chat."},
                status=status.HTTP_403_FORBIDDEN,
            )

        conversation, _ = GroupConversation.objects.get_or_create(group=group)

        read_message_ids = MessageReadReceipt.objects.filter(
            user=request.user,
            group_message__conversation=conversation
        ).values_list('group_message_id', flat=True)

        unread_messages = conversation.messages.exclude(
            id__in=read_message_ids
        ).exclude(sender=request.user)

        receipts = [
            MessageReadReceipt(user=request.user, group_message=msg)
            for msg in unread_messages
        ]
        MessageReadReceipt.objects.bulk_create(receipts, ignore_conflicts=True)

        return Response({"marked_read": len(receipts)}, status=status.HTTP_200_OK)

class UnreadCountAPIView(APIView):
    """Get total unread message count for the current user"""
    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(responses={200: "Unread count"})
    def get(self, request):
        user = request.user

        direct_unread = DirectMessage.objects.filter(
            conversation__in=DirectConversation.objects.filter(
                Q(user_a=user) | Q(user_b=user)
            ),
            is_read=False
        ).exclude(sender=user).count()

        user_groups = []
        if user.role == "admin":
            user_groups = Group.objects.all()
        elif user.role == "instructor":
            user_groups = Group.objects.filter(instructor=user)
        else:
            user_groups = user.student_groups.all()

        group_conversations = GroupConversation.objects.filter(group__in=user_groups)

        read_message_ids = MessageReadReceipt.objects.filter(
            user=user,
            group_message__conversation__in=group_conversations
        ).values_list('group_message_id', flat=True)

        group_unread = GroupMessage.objects.filter(
            conversation__in=group_conversations
        ).exclude(id__in=read_message_ids).exclude(sender=user).count()

        total_unread = direct_unread + group_unread

        return Response({
            "total": total_unread,
            "direct": direct_unread,
            "group": group_unread
        }, status=status.HTTP_200_OK)
