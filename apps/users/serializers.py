from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    default_avatar = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ("phone", "avatar", "default_avatar", "bio")

    def get_default_avatar(self, obj):
        seed = obj.user.username
        return f"https://api.dicebear.com/9.x/avataaars/svg?seed={seed}"


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    groups = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ("id", "username", "email", "first_name", "last_name", "role", "is_active", "profile", "groups")

    def get_groups(self, obj):
        from apps.groups.models import Group                               

        if obj.role == "student":
            qs = obj.student_groups.all()
        elif obj.role == "instructor":
            qs = obj.instructed_groups.all()
        else:
            return []
        return [{"id": g.id, "name": g.name} for g in qs]


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


class AdminUpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("username", "email", "first_name", "last_name", "role", "is_active")
        extra_kwargs = {
            "username": {"required": False},
            "email": {"required": False},
            "role": {"required": False},
            "is_active": {"required": False},
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


class AdminSetPasswordSerializer(serializers.Serializer):
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
