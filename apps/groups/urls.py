from django.urls import path

from . import api

urlpatterns = [
    path("", api.GroupListAPIView.as_view(), name="group_list"),
    path("<int:group_id>/", api.GroupDetailAPIView.as_view(), name="group_detail"),
]


