from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdmin

from .models import Lesson
from .serializers import LessonSerializer


def has_course_access(user, course):
    """Check if a user can access a course's content (lessons)."""
    if user.role in ("admin", "instructor"):
        return True
    if course.price == 0:
        return True
    # VIP subscription
    from apps.payments.models import CoursePurchase, Subscription
    if Subscription.objects.filter(user=user, status="active", plan__is_vip=True).exists():
        return True
    # Individual purchase
    if CoursePurchase.objects.filter(user=user, course=course).exists():
        return True
    return False


class LessonListAPIView(generics.ListCreateAPIView):
    serializer_class = LessonSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['course', 'user']

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdmin()]

    def get_queryset(self):
        user = self.request.user
        if user.role == "student":
            from apps.courses.models import Course
            # Students can access lessons from free courses, purchased courses, or if VIP
            from apps.payments.models import CoursePurchase, Subscription
            has_vip = Subscription.objects.filter(
                user=user, status="active", plan__is_vip=True
            ).exists()
            if has_vip:
                return Lesson.objects.all()
            # Free courses + purchased courses (use Q to avoid union subquery issue)
            from django.db.models import Q
            allowed_courses = Course.objects.filter(
                Q(price=0) | Q(purchases__user=user)
            ).distinct()
            return Lesson.objects.filter(course__in=allowed_courses)
        if user.role == "instructor":
            from apps.courses.models import Course
            allowed_courses = Course.objects.filter(groups__instructor=user).distinct()
            return Lesson.objects.filter(course__in=allowed_courses)
        return Lesson.objects.all()


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
        if not self._check_access(request.user, lesson):
            return Response({"detail": "You do not have access to this lesson."}, status=status.HTTP_403_FORBIDDEN)
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
