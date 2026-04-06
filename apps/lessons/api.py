from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.access import get_course_access_denial_message
from apps.users.permissions import IsAdmin

from .models import Lesson
from .serializers import LessonSerializer


def has_course_access(user, course):
    return get_course_access_denial_message(user, course) is None


class LessonListAPIView(generics.ListCreateAPIView):
    serializer_class = LessonSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['course', 'user']

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == "student":
            from django.db.models import Q
            return Lesson.objects.filter(
                course__groups__students=user
            ).filter(
                Q(course__price=0) | Q(course__purchases__user=user)
            ).distinct()
        if user.role == "instructor":
            from apps.courses.models import Course
            allowed_courses = Course.objects.filter(groups__instructor=user).distinct()
            return Lesson.objects.filter(course__in=allowed_courses)
        return Lesson.objects.all()

    def create(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "instructor"):
            return Response(
                {"detail": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )
        data = request.data.copy()
        if request.user.role == "instructor":
            from apps.courses.models import Course
            course_id = data.get("course")
            if not course_id:
                return Response(
                    {"course": ["This field is required."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not Course.objects.filter(pk=course_id, groups__instructor=request.user).exists():
                return Response(
                    {"detail": "This course is not assigned to you."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            data["user"] = request.user.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class LessonDetailAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdmin()]

    def _get_lesson(self, lesson_id):
        try:
            return Lesson.objects.select_related("course").get(pk=lesson_id)
        except Lesson.DoesNotExist:
            return None

    def _check_access(self, user, lesson):
        """Return True if user has access to this lesson's course."""
        return has_course_access(user, lesson.course)

    @swagger_auto_schema(responses={200: LessonSerializer})
    def get(self, request, lesson_id):
        lesson = self._get_lesson(lesson_id)
        if lesson is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        denial_message = get_course_access_denial_message(request.user, lesson.course)
        if denial_message:
            return Response({"detail": denial_message}, status=status.HTTP_403_FORBIDDEN)
        return Response(LessonSerializer(lesson).data)

    @swagger_auto_schema(request_body=LessonSerializer, responses={200: LessonSerializer})
    def put(self, request, lesson_id):
        lesson = self._get_lesson(lesson_id)
        if lesson is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = LessonSerializer(lesson, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(request_body=LessonSerializer, responses={200: LessonSerializer})
    def patch(self, request, lesson_id):
        lesson = self._get_lesson(lesson_id)
        if lesson is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = LessonSerializer(lesson, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, lesson_id):
        lesson = self._get_lesson(lesson_id)
        if lesson is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        lesson.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
