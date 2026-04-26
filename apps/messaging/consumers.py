from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.groups.models import Group

from .api import get_or_create_direct_conversation, user_can_access_group
from .models import DirectMessage, GroupConversation, GroupMessage
from .serializers import DirectMessageSerializer, GroupMessageSerializer

class DirectChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.target_user_id = int(self.scope["url_route"]["kwargs"]["user_id"])
        if self.target_user_id == user.id:
            await self.close(code=4002)
            return

        pair = sorted([user.id, self.target_user_id])
        self.room_name = f"dm_{pair[0]}_{pair[1]}"
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_name"):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        body = (content.get("message") or "").strip()
        if not body:
            await self.send_json({"error": "message is required"})
            return

        message_payload = await self._create_message(body)
        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "chat.message",
                "payload": message_payload,
            },
        )

    async def chat_message(self, event):
        await self.send_json(event["payload"])

    @database_sync_to_async
    def _create_message(self, body):
        user = self.scope["user"]
        target_user = type(user).objects.get(pk=self.target_user_id)
        conversation = get_or_create_direct_conversation(user, target_user)
        message = DirectMessage.objects.create(
            conversation=conversation,
            sender=user,
            body=body,
        )
        conversation.save(update_fields=["updated_at"])

        serialized_data = DirectMessageSerializer(message).data
        return serialized_data

class GroupChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.group_id = int(self.scope["url_route"]["kwargs"]["group_id"])
        can_access = await self._can_access_group(user.id, self.group_id)
        if not can_access:
            await self.close(code=4003)
            return

        self.room_name = f"group_chat_{self.group_id}"
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_name"):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        body = (content.get("message") or "").strip()
        if not body:
            await self.send_json({"error": "message is required"})
            return
        message_payload = await self._create_message(body)
        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "chat.message",
                "payload": message_payload,
            },
        )

    async def chat_message(self, event):
        await self.send_json(event["payload"])

    @database_sync_to_async
    def _can_access_group(self, user_id, group_id):
        from apps.users.models import User

        user = User.objects.get(pk=user_id)
        group = Group.objects.get(pk=group_id)
        return user_can_access_group(user, group)

    @database_sync_to_async
    def _create_message(self, body):
        user = self.scope["user"]
        group = Group.objects.get(pk=self.group_id)
        conversation, _ = GroupConversation.objects.get_or_create(group=group)
        message = GroupMessage.objects.create(
            conversation=conversation,
            sender=user,
            body=body,
        )
        conversation.save(update_fields=["updated_at"])

        serialized_data = GroupMessageSerializer(message).data
        return serialized_data
