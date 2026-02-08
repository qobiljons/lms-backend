from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import api

urlpatterns = [
    path("signup/", api.SignupAPIView.as_view(), name="signup"),
    path("login/", api.LoginAPIView.as_view(), name="login"),
    path("users/", api.UserListAPIView.as_view(), name="user_list"),
    path("me/", api.MeAPIView.as_view(), name="me"),
    path("logout/", api.LogoutAPIView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
