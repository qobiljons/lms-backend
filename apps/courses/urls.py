from django.urls import path

from . import api

urlpatterns = [
    path("", api.CourseListAPIView.as_view(), name="course_list"),
    path("<slug:slug>/", api.CourseDetailAPIView.as_view(), name="course_detail"),
]
