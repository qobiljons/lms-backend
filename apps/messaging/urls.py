from django.urls import path

from . import api

urlpatterns = [
    path("users/", api.ReachableUserListAPIView.as_view(), name="message_reachable_users"),
    path("direct/conversations/", api.DirectConversationListAPIView.as_view(), name="direct_conversation_list"),
    path("direct/<int:user_id>/", api.DirectMessagesAPIView.as_view(), name="direct_messages"),
    path("direct/<int:user_id>/read/", api.MarkDirectMessagesReadAPIView.as_view(), name="mark_direct_read"),
    path("groups/", api.GroupConversationListAPIView.as_view(), name="group_conversation_list"),
    path("groups/<int:group_id>/", api.GroupMessagesAPIView.as_view(), name="group_messages"),
    path("groups/<int:group_id>/read/", api.MarkGroupMessagesReadAPIView.as_view(), name="mark_group_read"),
    path("unread-count/", api.UnreadCountAPIView.as_view(), name="unread_count"),
]
