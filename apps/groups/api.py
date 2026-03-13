from django.contrib.auth import get_user_model
from django.db import models
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdmin
from apps.users.serializers import UserSerializer

from .models import Group
from .serializers import GroupDetailSerializer, GroupListSerializer

User = get_user_model()


class GroupPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class GroupListAPIView(generics.ListCreateAPIView):
    queryset = Group.objects.all()
    pagination_class = GroupPagination
    permission_classes = (permissions.IsAuthenticated, IsAdmin)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("name", "description")
    ordering_fields = ("name", "created_at")
    ordering = ("-created_at",)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return GroupDetailSerializer
        return GroupListSerializer


class GroupDetailAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def _get_group(self, group_id):
        try:
            return Group.objects.get(pk=group_id)
        except Group.DoesNotExist:
            return None

    @swagger_auto_schema(responses={200: GroupDetailSerializer})
    def get(self, request, group_id):
        group = self._get_group(group_id)
        if group is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(GroupDetailSerializer(group).data)

    @swagger_auto_schema(request_body=GroupDetailSerializer, responses={200: GroupDetailSerializer})
    def patch(self, request, group_id):
        group = self._get_group(group_id)
        if group is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = GroupDetailSerializer(group, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(GroupDetailSerializer(group).data)

    def delete(self, request, group_id):
        group = self._get_group(group_id)
        if group is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyGroupsAPIView(APIView):
    """Return the groups the current user belongs to, with full member details."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        user = request.user
        if user.role == "student":
            groups = user.student_groups.all()
        elif user.role == "instructor":
            groups = user.instructed_groups.all()
        else:
            groups = Group.objects.all()
        return Response(GroupDetailSerializer(groups, many=True).data)


class GroupMemberProfileAPIView(APIView):
    """View another user's profile — only if they share a group with you."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, username):
        try:
            target = User.objects.select_related("profile").get(username=username)
        except User.DoesNotExist:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        # Admins can view anyone
        if user.role == "admin":
            return Response(UserSerializer(target).data)

        # Students/instructors can only view members who share a group
        if user.role == "student":
            my_group_ids = user.student_groups.values_list("id", flat=True)
        elif user.role == "instructor":
            my_group_ids = user.instructed_groups.values_list("id", flat=True)
        else:
            my_group_ids = Group.objects.none().values_list("id", flat=True)

        # Check if target is in any of user's groups (as student or instructor)
        shares_group = Group.objects.filter(
            pk__in=my_group_ids,
        ).filter(
            models.Q(students=target) | models.Q(instructor=target)
        ).exists()

        if not shares_group:
            return Response(
                {"detail": "You can only view profiles of members in your groups."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(UserSerializer(target).data)
