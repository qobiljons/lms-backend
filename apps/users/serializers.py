from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ("phone", "avatar", "bio")


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = get_user_model()
        fields = ("id", "username", "email", "first_name", "last_name", "role", "profile")


class UpdateMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("username", "email", "first_name", "last_name")
        extra_kwargs = {
            "username": {"required": False},
            "email": {"required": False},
        }

    def validate_email(self, value):
        user = self.instance
        if get_user_model().objects.filter(email=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("email already in use")
        return value

    def validate_username(self, value):
        user = self.instance
        if get_user_model().objects.filter(username=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("username already in use")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate(self, attrs):
        user_model = get_user_model()
        if user_model.objects.filter(email=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "email already in use"})
        if user_model.objects.filter(username=attrs["username"]).exists():
            raise serializers.ValidationError({"username": "username already in use"})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user_model = get_user_model()
        user = user_model.objects.create_user(password=password, **validated_data)
        return user


class AdminCreateUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    role = serializers.ChoiceField(
        choices=["student", "instructor", "admin"],
        default="student",
    )

    def validate(self, attrs):
        user_model = get_user_model()
        if user_model.objects.filter(email=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "email already in use"})
        if user_model.objects.filter(username=attrs["username"]).exists():
            raise serializers.ValidationError({"username": "username already in use"})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user_model = get_user_model()
        user = user_model.objects.create_user(password=password, **validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs.get("username"),
            password=attrs.get("password"),
        )
        if user is None:
            raise serializers.ValidationError({"detail": "invalid credentials"})
        attrs["user"] = user
        return attrs
