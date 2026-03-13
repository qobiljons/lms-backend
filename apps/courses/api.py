from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdmin

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
        return [permissions.IsAuthenticated(), IsAdmin()]

    def get_queryset(self):
        user = self.request.user
        if user.role == "student":
            # Students ONLY see courses from their assigned groups
            return Course.objects.filter(groups__students=user).distinct()
        if user.role == "instructor":
            # Instructors see courses from groups they instruct
            return Course.objects.filter(groups__instructor=user).distinct()
        return Course.objects.all()


class CourseDetailAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdmin()]

    def _get_course(self, slug):
        try:
            return Course.objects.get(slug=slug)
        except Course.DoesNotExist:
            return None

    def _check_student_access(self, user, course):
        """Return True if student has group-based access to this course."""
        if user.role != "student":
            return True
        return course.groups.filter(students=user).exists()

    @swagger_auto_schema(responses={200: CourseSerializer})
    def get(self, request, slug):
        course = self._get_course(slug)
        if course is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        if not self._check_student_access(request.user, course):
            return Response({"detail": "You do not have access to this course."}, status=status.HTTP_403_FORBIDDEN)
        return Response(CourseSerializer(course).data)

    @swagger_auto_schema(request_body=CourseSerializer, responses={200: CourseSerializer})
    def put(self, request, slug):
        course = self._get_course(slug)
        if course is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CourseSerializer(course, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(request_body=CourseSerializer, responses={200: CourseSerializer})
    def patch(self, request, slug):
        course = self._get_course(slug)
        if course is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CourseSerializer(course, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, slug):
        course = self._get_course(slug)
        if course is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        course.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
