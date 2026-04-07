from django.urls import path

from . import api

urlpatterns = [
    path("", api.AttendanceSessionListCreateAPIView.as_view(), name="attendance_session_list"),
    path("overview/", api.AttendanceOverviewAPIView.as_view(), name="attendance_overview"),
    path("my/", api.MyAttendanceAPIView.as_view(), name="my_attendance"),
    path("<int:session_id>/", api.AttendanceSessionDetailAPIView.as_view(), name="attendance_session_detail"),
]
