from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdmin

from .access import get_course_access_denial_message
from .models import Course
from .serializers import CourseSerializer

class CoursePagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = "page_size"
    max_page_size = 1000

class CourseListAPIView(generics.ListCreateAPIView):
    serializer_class = CourseSerializer
    pagination_class = CoursePagination
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("title", "description")
    ordering_fields = ("title", "created_at")
    ordering = ("-created_at",)

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == "student":
            return Course.objects.filter(groups__students=user).distinct()
        if user.role == "instructor":
            return Course.objects.filter(groups__instructor=user).distinct()
        return Course.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def create(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "instructor"):
            return Response(
                {"detail": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)

class CourseDetailAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_permissions(self):
        if self.request.method in ("GET", "PUT", "PATCH"):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdmin()]

    def _get_course(self, slug):
        try:
            return Course.objects.get(slug=slug)
        except Course.DoesNotExist:
            return None

    @swagger_auto_schema(responses={200: CourseSerializer})
    def get(self, request, slug):
        course = self._get_course(slug)
        if course is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        denial_message = get_course_access_denial_message(request.user, course)
        if denial_message:
            return Response(
                {"detail": denial_message},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(CourseSerializer(course, context={"request": request}).data)

    @swagger_auto_schema(request_body=CourseSerializer, responses={200: CourseSerializer})
    def put(self, request, slug):
        course = self._get_course(slug)
        if course is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        denial_message = get_course_access_denial_message(request.user, course)
        if denial_message:
            return Response({"detail": denial_message}, status=status.HTTP_403_FORBIDDEN)
        serializer = CourseSerializer(course, data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(request_body=CourseSerializer, responses={200: CourseSerializer})
    def patch(self, request, slug):
        course = self._get_course(slug)
        if course is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        denial_message = get_course_access_denial_message(request.user, course)
        if denial_message:
            return Response({"detail": denial_message}, status=status.HTTP_403_FORBIDDEN)
        serializer = CourseSerializer(course, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, slug):
        course = self._get_course(slug)
        if course is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        course.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
