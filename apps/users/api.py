import io

from django_filters import rest_framework as django_filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, serializers as drf_serializers, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .permissions import IsAdmin
from .serializers import (
    AdminCreateUserSerializer,
    AdminSetPasswordSerializer,
    AdminUpdateUserSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    SignupSerializer,
    UpdateMeSerializer,
    UserProfileSerializer,
    UserSerializer,
)


def _get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class LogoutRequestSerializer(drf_serializers.Serializer):
    refresh = drf_serializers.CharField(help_text="The refresh token to blacklist")


class SignupAPIView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    @swagger_auto_schema(request_body=SignupSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = _get_tokens_for_user(user)
        return Response(
            {**UserSerializer(user).data, "tokens": tokens},
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    @swagger_auto_schema(request_body=LoginSerializer, responses={200: UserSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        tokens = _get_tokens_for_user(user)
        return Response({**UserSerializer(user).data, "tokens": tokens})


class UserPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = "page_size"
    max_page_size = 1000


class UserListAPIView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdmin)
    pagination_class = UserPagination
    filter_backends = (django_filters.DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ("role", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering_fields = ("username", "email", "date_joined")
    ordering = ("-date_joined",)

    def get_queryset(self):
        from django.contrib.auth import get_user_model
        return get_user_model().objects.all()


class UserDetailAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def _get_user(self, username):
        from django.contrib.auth import get_user_model
        try:
            return get_user_model().objects.get(username=username)
        except get_user_model().DoesNotExist:
            return None

    @swagger_auto_schema(responses={200: UserSerializer})
    def get(self, request, username):
        user = self._get_user(username)
        if user is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(UserSerializer(user).data)

    @swagger_auto_schema(request_body=AdminUpdateUserSerializer, responses={200: UserSerializer})
    def patch(self, request, username):
        user = self._get_user(username)
        if user is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdminUpdateUserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(user).data)

    def delete(self, request, username):
        user = self._get_user(username)
        if user is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminSetPasswordAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    @swagger_auto_schema(request_body=AdminSetPasswordSerializer)
    def post(self, request, username):
        from django.contrib.auth import get_user_model
        try:
            user = get_user_model().objects.get(username=username)
        except get_user_model().DoesNotExist:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdminSetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"detail": "password updated"})


class AdminCreateUserAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    @swagger_auto_schema(request_body=AdminCreateUserSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = AdminCreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class MeAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(responses={200: UserSerializer})
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @swagger_auto_schema(request_body=UpdateMeSerializer, responses={200: UserSerializer})
    def patch(self, request):
        serializer = UpdateMeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class ProfileAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(responses={200: UserProfileSerializer})
    def get(self, request):
        return Response(UserProfileSerializer(request.user.profile).data)

    @swagger_auto_schema(request_body=UserProfileSerializer, responses={200: UserProfileSerializer})
    def patch(self, request):
        serializer = UserProfileSerializer(
            request.user.profile, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserProfileSerializer(request.user.profile).data)


class ChangePasswordAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(request_body=ChangePasswordSerializer)
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"old_password": ["incorrect password"]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response({"detail": "password updated"})


class LogoutAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(request_body=LogoutRequestSerializer)
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"detail": "refresh token is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"success": True})
        except Exception:
            return Response(
                {"detail": "invalid token"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class DashboardStatsAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def _week_series(qs, date_field="created_at", weeks=7):
        """Return per-week counts for the last N weeks."""
        import datetime

        from django.db.models import Count
        from django.db.models.functions import TruncWeek
        from django.utils import timezone

        start = timezone.now() - datetime.timedelta(weeks=weeks)
        rows = (
            qs.filter(**{f"{date_field}__gte": start})
            .annotate(week=TruncWeek(date_field))
            .values("week")
            .annotate(count=Count("id"))
            .order_by("week")
        )
        lookup = {r["week"].strftime("%b %d"): r["count"] for r in rows}

        result = []
        for i in range(weeks):
            d = start + datetime.timedelta(weeks=i)
                             
            d = d - datetime.timedelta(days=d.weekday())
            label = d.strftime("%b %d")
            result.append({"week": label, "count": lookup.get(label, 0)})
        return result

    @staticmethod
    def _daily_series(qs, date_field="session_date", days=14):
        """Return per-day counts for the last N days using a date field."""
        import datetime

        from django.db.models import Count
        from django.utils import timezone

        start = (timezone.now() - datetime.timedelta(days=days)).date()
        rows = (
            qs.filter(**{f"{date_field}__gte": start})
            .values(date_field)
            .annotate(count=Count("id"))
            .order_by(date_field)
        )
        lookup = {r[date_field].strftime("%b %d"): r["count"] for r in rows}

        result = []
        for i in range(days):
            d = start + datetime.timedelta(days=i)
            label = d.strftime("%b %d")
            result.append({"day": label, "count": lookup.get(label, 0)})
        return result

    @staticmethod
    def _attendance_status_by_session(sessions_qs, limit=10):
        """Return per-session attendance breakdown for bar chart."""
        from django.db.models import Count, Q

        recent = sessions_qs.order_by("-session_date")[:limit]
        result = []
        for s in reversed(recent):
            records = s.records.all()
            total = records.count()
            present = records.filter(status__in=["attended", "attended_online", "late"]).count()
            absent = records.filter(status="absent").count()
            result.append({
                "session": s.session_date.strftime("%b %d"),
                "present": present,
                "absent": absent,
                "total": total,
            })
        return result

    @staticmethod
    def _revenue_series(weeks=8):
        """Return per-week revenue for the last N weeks."""
        import datetime
        from decimal import Decimal

        from django.db.models import Sum
        from django.db.models.functions import TruncWeek
        from django.utils import timezone

        from apps.payments.models import Payment

        start = timezone.now() - datetime.timedelta(weeks=weeks)
        rows = (
            Payment.objects.filter(status="succeeded", created_at__gte=start)
            .annotate(week=TruncWeek("created_at"))
            .values("week")
            .annotate(total=Sum("amount"))
            .order_by("week")
        )
        lookup = {r["week"].strftime("%b %d"): float(r["total"] or 0) for r in rows}

        result = []
        for i in range(weeks):
            d = start + datetime.timedelta(weeks=i)
            d = d - datetime.timedelta(days=d.weekday())
            label = d.strftime("%b %d")
            result.append({"week": label, "revenue": lookup.get(label, 0)})
        return result

    def get(self, request):
        from decimal import Decimal

        from django.contrib.auth import get_user_model
        from django.db.models import Avg, Count, Q, Sum
        from django.utils import timezone

        from apps.attendance.models import AttendanceRecord, AttendanceSession
        from apps.courses.models import Course
        from apps.groups.models import Group
        from apps.homework.models import Homework, HomeworkSubmission
        from apps.lessons.models import Lesson
        from apps.payments.models import CoursePurchase, Payment

        User = get_user_model()
        user = request.user

        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        if user.role == "admin":
            total_revenue = (
                Payment.objects.filter(status="succeeded").aggregate(total=Sum("amount"))["total"]
                or Decimal("0.00")
            )
            monthly_revenue = (
                Payment.objects.filter(status="succeeded", created_at__gte=month_start)
                .aggregate(total=Sum("amount"))["total"]
                or Decimal("0.00")
            )

            total_records = AttendanceRecord.objects.count()
            present_records = AttendanceRecord.objects.filter(
                status__in=["attended", "attended_online", "late"]
            ).count()
            attendance_rate = round((present_records / total_records * 100), 1) if total_records > 0 else 0

            recent_payments = Payment.objects.filter(status="succeeded").order_by("-created_at")[:5]

                        
            user_growth = self._week_series(User.objects.all(), "date_joined", weeks=8)
            revenue_trend = self._revenue_series(weeks=8)
            attendance_by_session = self._attendance_status_by_session(AttendanceSession.objects.all())

                                            
            att_status_dist = list(
                AttendanceRecord.objects.values("status")
                .annotate(count=Count("id"))
                .order_by("-count")
            )

                                                                
            course_pop = []
            for c in Course.objects.all()[:6]:
                student_count = User.objects.filter(student_groups__courses=c).distinct().count()
                course_pop.append({"name": c.title[:20], "students": student_count})

            return Response({
                "users": {
                    "total": User.objects.count(),
                    "active": User.objects.filter(is_active=True).count(),
                    "inactive": User.objects.filter(is_active=False).count(),
                    "students": User.objects.filter(role="student").count(),
                    "instructors": User.objects.filter(role="instructor").count(),
                    "admins": User.objects.filter(role="admin").count(),
                },
                "courses": {"total": Course.objects.count()},
                "lessons": {"total": Lesson.objects.count()},
                "groups": {"total": Group.objects.count()},
                "homework": {
                    "total": Homework.objects.count(),
                    "submissions": HomeworkSubmission.objects.count(),
                    "pending_grading": HomeworkSubmission.objects.filter(status="submitted").count(),
                },
                "attendance": {
                    "sessions": AttendanceSession.objects.count(),
                    "records": total_records,
                    "rate": attendance_rate,
                },
                "finance": {
                    "total_revenue": str(total_revenue),
                    "monthly_revenue": str(monthly_revenue),
                    "total_payments": Payment.objects.filter(status="succeeded").count(),
                },
                "recent_payments": [
                    {
                        "user": p.user.username,
                        "amount": str(p.amount),
                        "date": p.created_at.strftime("%b %d, %Y"),
                    }
                    for p in recent_payments
                ],
                "charts": {
                    "user_growth": user_growth,
                    "revenue_trend": revenue_trend,
                    "attendance_by_session": attendance_by_session,
                    "attendance_status_dist": att_status_dist,
                    "course_popularity": course_pop,
                },
            })

        elif user.role == "instructor":
            my_groups = Group.objects.filter(instructor=user)
            group_student_count = User.objects.filter(student_groups__in=my_groups).distinct().count()

            sessions = AttendanceSession.objects.filter(group__in=my_groups)
            records = AttendanceRecord.objects.filter(session__in=sessions)
            total_records = records.count()
            present_records = records.filter(status__in=["attended", "attended_online", "late"]).count()
            attendance_rate = round((present_records / total_records * 100), 1) if total_records > 0 else 0

            course_ids = my_groups.values_list("courses", flat=True).distinct()
            my_courses_count = Course.objects.filter(id__in=course_ids).count()

            my_lessons = Lesson.objects.filter(course__id__in=course_ids)
            hw_assignments = Homework.objects.filter(lesson__in=my_lessons)
            hw_submissions = HomeworkSubmission.objects.filter(homework__in=hw_assignments)

                        
            attendance_by_session = self._attendance_status_by_session(sessions)
            att_status_dist = list(
                records.values("status").annotate(count=Count("id")).order_by("-count")
            )

                               
            submission_trend = self._week_series(hw_submissions, "created_at", weeks=8)

                                      
            group_sizes = [
                {"name": g.name[:18], "students": g.students.count()}
                for g in my_groups[:6]
            ]

            return Response({
                "groups": {
                    "total": my_groups.count(),
                    "total_students": group_student_count,
                },
                "courses": {"total": my_courses_count},
                "lessons": {"total": my_lessons.count()},
                "homework": {
                    "total": hw_assignments.count(),
                    "submissions": hw_submissions.count(),
                    "pending_grading": hw_submissions.filter(status="submitted").count(),
                    "graded": hw_submissions.filter(status="graded").count(),
                },
                "attendance": {
                    "sessions": sessions.count(),
                    "records": total_records,
                    "rate": attendance_rate,
                },
                "charts": {
                    "attendance_by_session": attendance_by_session,
                    "attendance_status_dist": att_status_dist,
                    "submission_trend": submission_trend,
                    "group_sizes": group_sizes,
                },
            })

        else:           
            my_groups = user.student_groups.all()

            course_ids = my_groups.values_list("courses", flat=True).distinct()
            my_courses_count = Course.objects.filter(id__in=course_ids).count()

            purchased_count = CoursePurchase.objects.filter(user=user).count()

            my_records = AttendanceRecord.objects.filter(student=user)
            total_records = my_records.count()
            present_records = my_records.filter(status__in=["attended", "attended_online", "late"]).count()
            attendance_rate = round((present_records / total_records * 100), 1) if total_records > 0 else 0

            my_submissions = HomeworkSubmission.objects.filter(student=user)

            recent_records = my_records.select_related("session__group", "session__course").order_by("-session__session_date")[:5]

                        
            att_status_dist = list(
                my_records.values("status").annotate(count=Count("id")).order_by("-count")
            )

                                                   
            att_timeline = []
            recent_sessions = my_records.select_related("session").order_by("session__session_date")[:15]
            for r in recent_sessions:
                att_timeline.append({
                    "date": r.session.session_date.strftime("%b %d"),
                    "status": 1 if r.status in ["attended", "attended_online", "late"] else 0,
                    "label": r.status.replace("_", " ").title(),
                })

                                       
            score_trend = []
            graded = my_submissions.filter(score__isnull=False).order_by("graded_at")[:10]
            for s in graded:
                score_trend.append({
                    "name": s.homework.title[:15],
                    "score": float(s.score),
                    "total": s.homework.total_points,
                })

            return Response({
                "groups": {"total": my_groups.count()},
                "courses": {
                    "enrolled": my_courses_count,
                    "purchased": purchased_count,
                },
                "attendance": {
                    "total": total_records,
                    "present": present_records,
                    "rate": attendance_rate,
                },
                "homework": {
                    "submitted": my_submissions.filter(status="submitted").count(),
                    "graded": my_submissions.filter(status="graded").count(),
                    "draft": my_submissions.filter(status="draft").count(),
                    "total": my_submissions.count(),
                    "average_score": float(my_submissions.filter(score__isnull=False).aggregate(avg=Avg("score"))["avg"] or 0),
                },
                "recent_attendance": [
                    {
                        "group": r.session.group.name,
                        "course": r.session.course.title if r.session.course else "General",
                        "date": r.session.session_date.strftime("%b %d, %Y"),
                        "status": r.status,
                    }
                    for r in recent_records
                ],
                "charts": {
                    "attendance_status_dist": att_status_dist,
                    "attendance_timeline": att_timeline,
                    "score_trend": score_trend,
                },
            })


class ExportExcelAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get(self, request):
        from django.contrib.auth import get_user_model
        from django.http import HttpResponse
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        from openpyxl.utils import get_column_letter

        from apps.attendance.models import AttendanceRecord, AttendanceSession
        from apps.courses.models import Course
        from apps.groups.models import Group
        from apps.homework.models import Homework, HomeworkSubmission
        from apps.lessons.models import Lesson
        from apps.payments.models import CoursePurchase, Payment

        User = get_user_model()

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="16A34A", end_color="16A34A", fill_type="solid")

        def _write_sheet(wb, title, headers, rows):
            ws = wb.create_sheet(title=title)
            ws.append(headers)
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
            for row in rows:
                ws.append(row)
            for col_idx, _ in enumerate(headers, 1):
                max_len = max(
                    (len(str(ws.cell(row=r, column=col_idx).value or "")) for r in range(1, ws.max_row + 1)),
                    default=0,
                )
                ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 50)

        wb = Workbook()
        wb.remove(wb.active)

                  
        _write_sheet(
            wb, "Users",
            ["Email", "Username", "First Name", "Last Name", "Role", "Active", "Date Joined"],
            [
                [u.email, u.username, u.first_name, u.last_name, u.role, u.is_active, u.date_joined.strftime("%Y-%m-%d %H:%M")]
                for u in User.objects.all().order_by("id")
            ],
        )

                    
        _write_sheet(
            wb, "Courses",
            ["Title", "Description", "Price", "Created At"],
            [
                [c.title, c.description, float(c.price), c.created_at.strftime("%Y-%m-%d %H:%M")]
                for c in Course.objects.all().order_by("id")
            ],
        )

                   
        groups_qs = Group.objects.select_related("instructor").prefetch_related("students", "courses").order_by("id")
        _write_sheet(
            wb, "Groups",
            ["Name", "Description", "Instructor", "Student Count", "Course Count", "Created At"],
            [
                [g.name, g.description, g.instructor.username if g.instructor else "", g.students.count(), g.courses.count(), g.created_at.strftime("%Y-%m-%d %H:%M")]
                for g in groups_qs
            ],
        )

                    
        lessons_qs = Lesson.objects.select_related("course", "user").order_by("id")
        _write_sheet(
            wb, "Lessons",
            ["Title", "Course", "Instructor", "Created At"],
            [
                [l.title, l.course.title, l.user.username, l.created_at.strftime("%Y-%m-%d %H:%M")]
                for l in lessons_qs
            ],
        )

                     
        payments_qs = Payment.objects.select_related("user").order_by("id")
        _write_sheet(
            wb, "Payments",
            ["User", "Amount", "Currency", "Status", "Created At"],
            [
                [p.user.username, float(p.amount), p.currency, p.status, p.created_at.strftime("%Y-%m-%d %H:%M")]
                for p in payments_qs
            ],
        )

                             
        purchases_qs = CoursePurchase.objects.select_related("user", "course").order_by("id")
        _write_sheet(
            wb, "Course Purchases",
            ["User", "Course", "Amount", "Created At"],
            [
                [cp.user.username, cp.course.title, float(cp.amount), cp.created_at.strftime("%Y-%m-%d %H:%M")]
                for cp in purchases_qs
            ],
        )

                                
        sessions_qs = AttendanceSession.objects.select_related("group", "course", "taken_by").order_by("id")
        _write_sheet(
            wb, "Attendance Sessions",
            ["Group", "Course", "Taken By", "Session Date"],
            [
                [s.group.name, s.course.title if s.course else "", s.taken_by.username if s.taken_by else "", s.session_date.strftime("%Y-%m-%d")]
                for s in sessions_qs
            ],
        )

                               
        records_qs = AttendanceRecord.objects.select_related("student", "session__group", "session__course").order_by("id")
        _write_sheet(
            wb, "Attendance Records",
            ["Student", "Group", "Course", "Session Date", "Status"],
            [
                [r.student.username, r.session.group.name, r.session.course.title if r.session.course else "", r.session.session_date.strftime("%Y-%m-%d"), r.status]
                for r in records_qs
            ],
        )

                     
        hw_qs = Homework.objects.select_related("lesson__course", "created_by").order_by("id")
        _write_sheet(
            wb, "Homework",
            ["Title", "Lesson", "Course", "Total Points", "Due Date", "Created By"],
            [
                [h.title, h.lesson.title, h.lesson.course.title, h.total_points, h.due_date.strftime("%Y-%m-%d %H:%M") if h.due_date else "", h.created_by.username if h.created_by else ""]
                for h in hw_qs
            ],
        )

                                  
        subs_qs = HomeworkSubmission.objects.select_related("student", "homework", "graded_by").order_by("id")
        _write_sheet(
            wb, "Homework Submissions",
            ["Student", "Homework", "Status", "Score", "Graded By", "Submitted At"],
            [
                [s.student.username, s.homework.title, s.status, float(s.score) if s.score is not None else "", s.graded_by.username if s.graded_by else "", s.submitted_at.strftime("%Y-%m-%d %H:%M") if s.submitted_at else ""]
                for s in subs_qs
            ],
        )

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        response = HttpResponse(
            buf.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="lms_export.xlsx"'
        return response
