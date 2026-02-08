from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, serializers as drf_serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .permissions import IsAdmin
from .serializers import LoginSerializer, SignupSerializer, UserSerializer


def _get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class LogoutRequestSerializer(drf_serializers.Serializer):
    refresh = drf_serializers.CharField(help_text="The refresh token to blacklist")


class SignupAPIView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    @swagger_auto_schema(request_body=SignupSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = _get_tokens_for_user(user)
        return Response(
            {**UserSerializer(user).data, "tokens": tokens},
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    @swagger_auto_schema(request_body=LoginSerializer, responses={200: UserSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        tokens = _get_tokens_for_user(user)
        return Response({**UserSerializer(user).data, "tokens": tokens})


class UserListAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    @swagger_auto_schema(responses={200: UserSerializer(many=True)})
    def get(self, request):
        from django.contrib.auth import get_user_model
        users = get_user_model().objects.all()
        return Response(UserSerializer(users, many=True).data)


class MeAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(responses={200: UserSerializer})
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class LogoutAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(request_body=LogoutRequestSerializer)
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"detail": "refresh token is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"success": True})
        except Exception:
            return Response(
                {"detail": "invalid token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
