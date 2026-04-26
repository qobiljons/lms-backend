from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Homework, HomeworkFile, HomeworkSubmission
from .serializers import (
    HomeworkFileSerializer,
    HomeworkSerializer,
    HomeworkSubmissionCreateSerializer,
    HomeworkSubmissionSerializer,
)

class HomeworkListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return HomeworkSerializer
        return HomeworkSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Homework.objects.select_related(
            "lesson", "lesson__course", "created_by"
        ).prefetch_related("submissions")

        lesson_id = self.request.query_params.get("lesson")
        if lesson_id:
            queryset = queryset.filter(lesson_id=lesson_id)

        if user.role == "student":
            queryset = queryset.filter(
                lesson__course__groups__students=user
            ).distinct()
        elif user.role == "instructor":
            queryset = queryset.filter(
                lesson__course__groups__instructor=user
            ).distinct()

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def create(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "instructor"):
            return Response(
                {"detail": "Only admins and instructors can create homework."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class HomeworkDetailAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def _get_homework(self, homework_id):
        try:
            return Homework.objects.select_related(
                "lesson", "created_by"
            ).prefetch_related("submissions").get(pk=homework_id)
        except Homework.DoesNotExist:
            return None

    @swagger_auto_schema(responses={200: HomeworkSerializer})
    def get(self, request, homework_id):
        homework = self._get_homework(homework_id)
        if not homework:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(HomeworkSerializer(homework, context={"request": request}).data)

    @swagger_auto_schema(request_body=HomeworkSerializer, responses={200: HomeworkSerializer})
    def patch(self, request, homework_id):
        if request.user.role not in ("admin", "instructor"):
            return Response(
                {"detail": "Only admins and instructors can update homework."},
                status=status.HTTP_403_FORBIDDEN,
            )
        homework = self._get_homework(homework_id)
        if not homework:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = HomeworkSerializer(homework, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, homework_id):
        if request.user.role not in ("admin", "instructor"):
            return Response(
                {"detail": "Only admins and instructors can delete homework."},
                status=status.HTTP_403_FORBIDDEN,
            )
        homework = self._get_homework(homework_id)
        if not homework:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        homework.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class HomeworkSubmissionListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return HomeworkSubmissionCreateSerializer
        return HomeworkSubmissionSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = HomeworkSubmission.objects.select_related(
            "homework", "homework__lesson", "student", "graded_by"
        ).prefetch_related("uploaded_files")

        homework_id = self.request.query_params.get("homework")
        if homework_id:
            queryset = queryset.filter(homework_id=homework_id)

        if user.role == "student":
            queryset = queryset.filter(student=user)

        elif user.role == "instructor":
            queryset = queryset.filter(
                homework__lesson__course__groups__instructor=user
            ).distinct()

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

class HomeworkSubmissionDetailAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def _get_submission(self, submission_id):
        try:
            return HomeworkSubmission.objects.select_related(
                "homework", "student", "graded_by"
            ).prefetch_related("uploaded_files").get(pk=submission_id)
        except HomeworkSubmission.DoesNotExist:
            return None

    @swagger_auto_schema(responses={200: HomeworkSubmissionSerializer})
    def get(self, request, submission_id):
        submission = self._get_submission(submission_id)
        if not submission:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role == "student" and submission.student != request.user:
            return Response(
                {"detail": "You can only view your own submissions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(HomeworkSubmissionSerializer(submission).data)

    @swagger_auto_schema(
        request_body=HomeworkSubmissionSerializer,
        responses={200: HomeworkSubmissionSerializer},
    )
    def patch(self, request, submission_id):
        submission = self._get_submission(submission_id)
        if not submission:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role == "student":
            if submission.student != request.user:
                return Response(
                    {"detail": "You can only update your own submissions."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if submission.status == "graded":
                return Response(
                    {"detail": "Cannot update a graded submission."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = HomeworkSubmissionCreateSerializer(
                submission, data=request.data, partial=True, context={"request": request}
            )
        else:

            serializer = HomeworkSubmissionSerializer(
                submission, data=request.data, partial=True
            )
            if "score" in request.data or "feedback" in request.data:
                request.data["graded_at"] = timezone.now()
                request.data["graded_by"] = request.user.id
                request.data["status"] = "graded"

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(HomeworkSubmissionSerializer(submission).data)

class HomeworkFileUploadAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        operation_description="Upload a file for homework submission",
        responses={201: HomeworkFileSerializer},
    )
    def post(self, request, submission_id):
        try:
            submission = HomeworkSubmission.objects.get(pk=submission_id)
        except HomeworkSubmission.DoesNotExist:
            return Response({"detail": "Submission not found"}, status=status.HTTP_404_NOT_FOUND)

        if submission.student != request.user:
            return Response(
                {"detail": "You can only upload files to your own submissions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if submission.status == "graded":
            return Response(
                {"detail": "Cannot upload files to a graded submission."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response(
                {"detail": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        homework_file = HomeworkFile.objects.create(
            submission=submission,
            file=uploaded_file,
            filename=uploaded_file.name,
            file_type=uploaded_file.content_type,
            file_size=uploaded_file.size,
        )

        return Response(
            HomeworkFileSerializer(homework_file).data,
            status=status.HTTP_201_CREATED,
        )
