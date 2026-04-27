from django.db.models import Q
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


def _student_accessible_course_ids(user):
    """Course IDs a student has access to: free courses OR courses they've purchased."""
    from apps.courses.models import Course
    from apps.payments.models import CoursePurchase

    free_ids = list(Course.objects.filter(price=0).values_list("id", flat=True))
    purchased_ids = list(
        CoursePurchase.objects.filter(user=user).values_list("course_id", flat=True)
    )
    return set(free_ids) | set(purchased_ids)


def _student_can_access_homework(user, homework):
    """True if the student has access to the course this homework belongs to."""
    if not homework.lesson_id or not homework.lesson.course_id:
        return False
    course = homework.lesson.course
    if course.price == 0:
        return True
    from apps.payments.models import CoursePurchase
    return CoursePurchase.objects.filter(user=user, course=course).exists()

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
            accessible_ids = _student_accessible_course_ids(user)
            queryset = queryset.filter(lesson__course_id__in=accessible_ids).distinct()
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
        if request.user.role == "student" and not _student_can_access_homework(request.user, homework):
            return Response(
                {"detail": "This homework belongs to a course you haven't purchased."},
                status=status.HTTP_403_FORBIDDEN,
            )
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

    def create(self, request, *args, **kwargs):
        if request.user.role == "student":
            hw_id = request.data.get("homework")
            if hw_id:
                try:
                    hw = Homework.objects.select_related("lesson__course").get(pk=hw_id)
                except Homework.DoesNotExist:
                    return Response({"detail": "Homework not found."}, status=status.HTTP_404_NOT_FOUND)
                if not _student_can_access_homework(request.user, hw):
                    return Response(
                        {"detail": "Purchase the course to start this homework."},
                        status=status.HTTP_403_FORBIDDEN,
                    )
        return super().create(request, *args, **kwargs)

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
            serializer = HomeworkSubmissionCreateSerializer(
                submission, data=request.data, partial=True, context={"request": request}
            )
        else:

            serializer = HomeworkSubmissionSerializer(
                submission, data=request.data, partial=True
            )

        serializer.is_valid(raise_exception=True)
        if request.user.role != "student" and ("score" in request.data or "feedback" in request.data):
            serializer.save(
                graded_at=timezone.now(),
                graded_by=request.user,
                status="graded",
            )
        else:
            serializer.save()
        return Response(HomeworkSubmissionSerializer(submission).data)

class HomeworkFileUploadAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    ALLOWED_EXTS = {
        ".py", ".sql", ".txt", ".md", ".csv", ".json", ".zip",
        ".pbit", ".pbix", ".pdf", ".dax", ".dtsx", ".sln", ".dtproj",
        ".xlsx", ".xls", ".docx", ".rtf",
    }
    MAX_SIZE_BYTES = 50 * 1024 * 1024

    @swagger_auto_schema(
        operation_description="Upload a file for homework submission",
        responses={201: HomeworkFileSerializer},
    )
    def post(self, request, submission_id):
        import os

        try:
            submission = HomeworkSubmission.objects.get(pk=submission_id)
        except HomeworkSubmission.DoesNotExist:
            return Response({"detail": "Submission not found"}, status=status.HTTP_404_NOT_FOUND)

        if submission.student != request.user:
            return Response(
                {"detail": "You can only upload files to your own submissions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response(
                {"detail": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in self.ALLOWED_EXTS:
            return Response(
                {"detail": f"File type '{ext}' is not allowed. Accepted: {', '.join(sorted(self.ALLOWED_EXTS))}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if uploaded_file.size > self.MAX_SIZE_BYTES:
            return Response(
                {"detail": f"File too large (max {self.MAX_SIZE_BYTES // (1024*1024)} MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content_type = uploaded_file.content_type or "application/octet-stream"
        if len(content_type) > 50:
            content_type = content_type[:50]

        homework_file = HomeworkFile.objects.create(
            submission=submission,
            file=uploaded_file,
            filename=uploaded_file.name,
            file_type=content_type,
            file_size=uploaded_file.size,
        )

        if submission.status in ("graded", "submitted"):
            submission.status = "draft"
            submission.save(update_fields=["status", "updated_at"])

        return Response(
            HomeworkFileSerializer(homework_file).data,
            status=status.HTTP_201_CREATED,
        )


class AIAutoGradeAPIView(APIView):
    """Auto-grade a HomeworkSubmission using AI evaluators.

    POST /homework/submissions/<submission_id>/ai-grade/
    Body:
        {
            "type": "power_bi" | "python" | "sql" | "ssis",
            "apply": bool   (optional, default false — if true, writes score+feedback)
        }

    Returns:
        { "score": int, "feedback": str, "raw": {...}, "evaluator": "..." }
    """

    permission_classes = (permissions.IsAuthenticated,)

    SUPPORTED_TYPES = {"power_bi", "python", "sql", "ssis"}

    def _can_grade(self, user, submission):
        if user.role == "admin":
            return True
        if user.role == "instructor":
            try:
                course = submission.homework.lesson.course
                return course.groups.filter(instructor=user).exists()
            except Exception:
                return False
        if user.role == "student":
            return submission.student_id == user.id
        return False

    def _collect_files_to_tempdir(self, submission, tmpdir):
        """Copy all uploaded files from the submission into a flat temp dir.
        ZIP archives are extracted in-place. Returns list of resulting file paths."""
        import os
        import shutil
        import zipfile

        copied = []
        for hf in submission.uploaded_files.all():
            if not hf.file:
                continue
            try:
                src_path = hf.file.path
            except Exception:
                continue
            if not os.path.exists(src_path):
                continue
            fname = hf.filename or os.path.basename(src_path)
            dest = os.path.join(tmpdir, fname)
            base, ext = os.path.splitext(dest)
            counter = 1
            while os.path.exists(dest):
                dest = f"{base}_{counter}{ext}"
                counter += 1
            shutil.copy2(src_path, dest)

            if ext.lower() == ".zip" and zipfile.is_zipfile(dest):
                extract_dir = os.path.join(tmpdir, os.path.splitext(os.path.basename(dest))[0])
                os.makedirs(extract_dir, exist_ok=True)
                try:
                    with zipfile.ZipFile(dest, "r") as zf:
                        for member in zf.namelist():
                            if member.startswith("/") or ".." in member.split("/"):
                                continue
                            zf.extract(member, extract_dir)
                    for root, _dirs, files in os.walk(extract_dir):
                        for f in files:
                            copied.append(os.path.join(root, f))
                except zipfile.BadZipFile:
                    copied.append(dest)
            else:
                copied.append(dest)
        return copied

    def _build_question_dicts(self, homework):
        """Turn homework.questions JSON into the {key: text} dicts PowerBIMentor expects."""
        questions = {}
        prompts = {}
        for i, q in enumerate(homework.questions or []):
            key = q.get("key") or q.get("type") or f"q{i+1}"
            questions[key] = q.get("question") or q.get("text") or homework.description
            prompts[key] = q.get("prompt") or "Evaluate the student's work for correctness, clarity, and best practices."
        if not questions:
            questions = {"answer": homework.description or homework.title}
            prompts = {"answer": "Evaluate the student's submission for correctness, clarity, and best practices."}
        return questions, prompts

    def _evaluate_power_bi(self, submission, target_path):
        from django.conf import settings
        from PowerBIMentor import PowerBIMentor

        api_key = getattr(settings, "GEMINI_API_KEY", None)
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured on the server.")

        questions, prompts = self._build_question_dicts(submission.homework)

        mentor = PowerBIMentor(api_key=api_key)
        result = mentor.evaluate_all(
            answer_path=target_path,
            questions=questions,
            prompts=prompts,
        )
        return result

    def _evaluate_quantum(self, submission, target_path, qtype):
        import asyncio

        from django.conf import settings
        from QuantumCheck import HomeworkEvaluator

        api_key = getattr(settings, "GEMINI_API_KEY", None)
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured on the server.")

        question_content = (
            submission.homework.description
            or submission.homework.title
            or "Evaluate this submission."
        )

        async def run():
            evaluator = HomeworkEvaluator()
            return await evaluator.evaluate_from_content(
                question_content=question_content,
                answer_path=target_path,
                question_type=qtype,
                api_key=api_key,
            )

        return asyncio.run(run())

    def post(self, request, submission_id):
        import os
        import tempfile

        try:
            submission = HomeworkSubmission.objects.select_related(
                "homework__lesson__course", "student"
            ).get(pk=submission_id)
        except HomeworkSubmission.DoesNotExist:
            return Response({"detail": "submission not found"}, status=status.HTTP_404_NOT_FOUND)

        if not self._can_grade(request.user, submission):
            return Response(
                {"detail": "You do not have permission to auto-grade this submission."},
                status=status.HTTP_403_FORBIDDEN,
            )

        qtype = (request.data.get("type") or "").lower()
        if qtype not in self.SUPPORTED_TYPES:
            return Response(
                {"detail": f"type must be one of {sorted(self.SUPPORTED_TYPES)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        apply_grade = bool(request.data.get("apply", False))
        if request.user.role == "student":
            apply_grade = False

        with tempfile.TemporaryDirectory(prefix="hw_grade_") as tmp:
            files = self._collect_files_to_tempdir(submission, tmp)
            if not files:
                return Response(
                    {"detail": "No files attached to this submission."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            TYPE_EXTS = {
                "python": {".py"},
                "sql": {".sql", ".txt"},
                "ssis": {".dtsx", ".sln", ".dtproj"},
                "power_bi": {".pbit", ".pbix", ".pdf"},
            }
            relevant_exts = TYPE_EXTS.get(qtype, set())
            relevant = [f for f in files if os.path.splitext(f)[1].lower() in relevant_exts]
            if not relevant:
                relevant = files
            target_path = relevant[0] if len(relevant) == 1 else tmp

            try:
                if qtype == "power_bi":
                    raw = self._evaluate_power_bi(submission, target_path)
                else:
                    raw = self._evaluate_quantum(submission, relevant[0] if relevant else files[0], qtype)
            except ImportError as e:
                return Response(
                    {"detail": f"Evaluator package not installed on server: {e}"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            except Exception as e:
                return Response(
                    {"detail": f"AI evaluation failed: {e}"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            score = raw.get("score") if isinstance(raw, dict) else None
            feedback = raw.get("feedback") if isinstance(raw, dict) else str(raw)

            submission.ai_feedback = {
                "evaluator": "PowerBIMentor" if qtype == "power_bi" else "QuantumChecker",
                "type": qtype,
                "score": score,
                "feedback": feedback,
                "raw": raw if isinstance(raw, (dict, list, str, int, float, bool, type(None))) else str(raw),
                "graded_at": timezone.now().isoformat(),
                "graded_by": request.user.username,
            }

            if apply_grade and score is not None:
                from decimal import Decimal
                try:
                    pct = float(score) / 100.0
                    submission.score = round(Decimal(submission.homework.total_points) * Decimal(pct), 2)
                except Exception:
                    pass
                if feedback:
                    submission.feedback = feedback
                submission.status = "graded"
                submission.graded_at = timezone.now()
                submission.graded_by = request.user

            submission.save()

        return Response({
            "evaluator": submission.ai_feedback.get("evaluator"),
            "type": qtype,
            "score": score,
            "feedback": feedback,
            "applied": apply_grade,
            "submission_score": str(submission.score) if submission.score is not None else None,
            "raw": submission.ai_feedback.get("raw"),
        })
