from django.urls import path

from . import api

urlpatterns = [
    path("", api.GroupListAPIView.as_view(), name="group_list"),
    path("my/", api.MyGroupsAPIView.as_view(), name="my_groups"),
    path("members/<str:username>/", api.GroupMemberProfileAPIView.as_view(), name="group_member_profile"),
    path("<int:group_id>/", api.GroupDetailAPIView.as_view(), name="group_detail"),
]

