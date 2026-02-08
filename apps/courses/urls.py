from django.urls import path

from . import api

urlpatterns = [
    path("", api.CourseListAPIView.as_view(), name="course_list"),
    path("<int:course_id>/", api.CourseDetailAPIView.as_view(), name="course_detail"),
]
