from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import api

urlpatterns = [
    path("login/", api.LoginAPIView.as_view(), name="login"),
    path("users/", api.UserListAPIView.as_view(), name="user_list"),
    path("users/create/", api.AdminCreateUserAPIView.as_view(), name="admin_create_user"),
    path("users/<str:username>/", api.UserDetailAPIView.as_view(), name="user_detail"),
    path("users/<str:username>/set-password/", api.AdminSetPasswordAPIView.as_view(), name="admin_set_password"),
    path("me/", api.MeAPIView.as_view(), name="me"),
    path("me/profile/", api.ProfileAPIView.as_view(), name="me_profile"),
    path("me/change-password/", api.ChangePasswordAPIView.as_view(), name="change_password"),
    path("logout/", api.LogoutAPIView.as_view(), name="logout"),
    path("dashboard/stats/", api.DashboardStatsAPIView.as_view(), name="dashboard_stats"),
    path("dashboard/revenue-trend/", api.RevenueTrendAPIView.as_view(), name="dashboard_revenue_trend"),
    path("ai/chat/", api.AIChatAPIView.as_view(), name="ai_chat"),
    path("export/excel/", api.ExportExcelAPIView.as_view(), name="export_excel"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
