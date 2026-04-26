from django.db.models import Count, Q
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AttendanceRecord, AttendanceSession
from .serializers import AttendanceSessionSerializer, AttendanceSessionWriteSerializer

def _get_attendance_queryset_for_user(user):
    queryset = AttendanceSession.objects.select_related(
        "group", "course", "taken_by"
    ).prefetch_related("records__student")
    if user.role == "admin":
        return queryset
    if user.role == "instructor":
        return queryset.filter(group__instructor=user)
    return queryset.filter(records__student=user).distinct()

def _can_manage_attendance(user, session):
    if user.role == "admin":
        return True
    return user.role == "instructor" and session.group.instructor_id == user.id

class AttendancePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

class AttendanceSessionListCreateAPIView(generics.ListCreateAPIView):
    pagination_class = AttendancePagination
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("group__name", "course__title", "note")
    ordering_fields = ("session_date", "created_at")
    ordering = ("-session_date", "-created_at")

    def get_queryset(self):
        queryset = _get_attendance_queryset_for_user(self.request.user)

        group_id = self.request.query_params.get("group")
        if group_id:
            queryset = queryset.filter(group_id=group_id)

        course_id = self.request.query_params.get("course")
        if course_id:
            queryset = queryset.filter(course_id=course_id)

        session_date = self.request.query_params.get("session_date")
        if session_date:
            queryset = queryset.filter(session_date=session_date)

        return queryset

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AttendanceSessionWriteSerializer
        return AttendanceSessionSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "instructor"):
            return Response(
                {"detail": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        group = serializer.validated_data["group"]
        if request.user.role == "instructor" and group.instructor_id != request.user.id:
            return Response(
                {"detail": "You can only take attendance for your own groups."},
                status=status.HTTP_403_FORBIDDEN,
            )

        session = serializer.save()
        return Response(
            AttendanceSessionSerializer(session).data, status=status.HTTP_201_CREATED
        )

class AttendanceSessionDetailAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def _get_session(self, session_id):
        try:
            return AttendanceSession.objects.select_related(
                "group", "course", "taken_by"
            ).prefetch_related("records__student").get(pk=session_id)
        except AttendanceSession.DoesNotExist:
            return None

    @swagger_auto_schema(responses={200: AttendanceSessionSerializer})
    def get(self, request, session_id):
        session = self._get_session(session_id)
        if session is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        if not _get_attendance_queryset_for_user(request.user).filter(pk=session.pk).exists():
            return Response(
                {"detail": "You do not have permission to view this attendance session."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(AttendanceSessionSerializer(session).data)

    @swagger_auto_schema(
        request_body=AttendanceSessionWriteSerializer,
        responses={200: AttendanceSessionSerializer},
    )
    def patch(self, request, session_id):
        session = self._get_session(session_id)
        if session is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        if not _can_manage_attendance(request.user, session):
            return Response(
                {"detail": "You do not have permission to update this attendance session."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AttendanceSessionWriteSerializer(
            session, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        group = serializer.validated_data.get("group")
        if request.user.role == "instructor" and group and group.instructor_id != request.user.id:
            return Response(
                {"detail": "You can only assign your own groups."},
                status=status.HTTP_403_FORBIDDEN,
            )
        updated_session = serializer.save()
        return Response(AttendanceSessionSerializer(updated_session).data)

    def delete(self, request, session_id):
        session = self._get_session(session_id)
        if session is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        if not _can_manage_attendance(request.user, session):
            return Response(
                {"detail": "You do not have permission to delete this attendance session."},
                status=status.HTTP_403_FORBIDDEN,
            )
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AttendanceOverviewAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        if request.user.role not in ("admin", "instructor"):
            return Response(
                {"detail": "Only admins and instructors can view attendance overview."},
                status=status.HTTP_403_FORBIDDEN,
            )

        sessions = _get_attendance_queryset_for_user(request.user)
        records = AttendanceRecord.objects.filter(session__in=sessions)
        status_counts = {
            key: records.filter(status=key).count()
            for key in (
                AttendanceRecord.Status.ATTENDED,
                AttendanceRecord.Status.ATTENDED_ONLINE,
                AttendanceRecord.Status.ABSENT,
                AttendanceRecord.Status.LATE,
                AttendanceRecord.Status.EXCUSED,
            )
        }
        present = (
            status_counts[AttendanceRecord.Status.ATTENDED]
            + status_counts[AttendanceRecord.Status.ATTENDED_ONLINE]
            + status_counts[AttendanceRecord.Status.LATE]
        )
        total = sum(status_counts.values())
        percentage = round((present / total) * 100, 2) if total else 0

        group_stats = (
            sessions.values("group_id", "group__name")
            .annotate(total_sessions=Count("id"))
            .order_by("group__name")
        )

        return Response(
            {
                "total_sessions": sessions.count(),
                "total_records": total,
                "attendance_percentage": percentage,
                "status_breakdown": status_counts,
                "groups": list(group_stats),
            }
        )

class MyAttendanceAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        user = request.user
        records = AttendanceRecord.objects.select_related(
            "session", "session__group", "session__course"
        ).filter(student=user)

        status_counts = {
            key: records.filter(status=key).count()
            for key in (
                AttendanceRecord.Status.ATTENDED,
                AttendanceRecord.Status.ATTENDED_ONLINE,
                AttendanceRecord.Status.ABSENT,
                AttendanceRecord.Status.LATE,
                AttendanceRecord.Status.EXCUSED,
            )
        }

        present = (
            status_counts[AttendanceRecord.Status.ATTENDED]
            + status_counts[AttendanceRecord.Status.ATTENDED_ONLINE]
            + status_counts[AttendanceRecord.Status.LATE]
        )
        total = sum(status_counts.values())
        percentage = round((present / total) * 100, 2) if total else 0

        by_group = (
            records.values("session__group_id", "session__group__name")
            .annotate(
                total=Count("id"),
                present=Count(
                    "id",
                    filter=Q(
                        status__in=[
                            AttendanceRecord.Status.ATTENDED,
                            AttendanceRecord.Status.ATTENDED_ONLINE,
                            AttendanceRecord.Status.LATE,
                        ]
                    ),
                ),
            )
            .order_by("session__group__name")
        )

        for row in by_group:
            row["attendance_percentage"] = round(
                (row["present"] / row["total"]) * 100, 2
            ) if row["total"] else 0

        recent_records = records.order_by("-session__session_date", "-marked_at")[:10]
        recent_payload = [
            {
                "session_id": record.session_id,
                "group": record.session.group.name,
                "course": record.session.course.title if record.session.course else None,
                "session_date": record.session.session_date,
                "status": record.status,
                "note": record.note,
            }
            for record in recent_records
        ]

        return Response(
            {
                "summary": {
                    "total_records": total,
                    "present_records": present,
                    "attendance_percentage": percentage,
                    "status_breakdown": status_counts,
                },
                "by_group": list(by_group),
                "recent_records": recent_payload,
            }
        )
