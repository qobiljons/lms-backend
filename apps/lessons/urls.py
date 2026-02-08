from django.urls import path

from . import api

urlpatterns = [
    path("", api.LessonListAPIView.as_view(), name="lesson_list"),
    path("<int:lesson_id>/", api.LessonDetailAPIView.as_view(), name="lesson_detail"),
]
