from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdmin

from .models import Lesson
from .serializers import LessonSerializer


class LessonListAPIView(generics.ListCreateAPIView):
    serializer_class = LessonSerializer
    queryset = Lesson.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['course', 'user']

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdmin()]


class LessonDetailAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdmin()]

    def _get_lesson(self, lesson_id):
        try:
            return Lesson.objects.get(pk=lesson_id)
        except Lesson.DoesNotExist:
            return None

    @swagger_auto_schema(responses={200: LessonSerializer})
    def get(self, request, lesson_id):
        lesson = self._get_lesson(lesson_id)
        if lesson is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
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
