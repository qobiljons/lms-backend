from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdmin

from .models import Group
from .serializers import GroupDetailSerializer, GroupListSerializer


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
