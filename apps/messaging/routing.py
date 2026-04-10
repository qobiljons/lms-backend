from django.urls import path

from .consumers import DirectChatConsumer, GroupChatConsumer

websocket_urlpatterns = [
    path("ws/messages/direct/<int:user_id>/", DirectChatConsumer.as_asgi()),
    path("ws/messages/groups/<int:group_id>/", GroupChatConsumer.as_asgi()),
]
