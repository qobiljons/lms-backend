from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from .models import AttendanceRecord, AttendanceSession

User = get_user_model()


class AttendanceStudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name")


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_detail = AttendanceStudentSerializer(source="student", read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = ("id", "student", "student_detail", "status", "note", "marked_at")
        read_only_fields = ("id", "marked_at")


class AttendanceRecordWriteSerializer(serializers.Serializer):
    student = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role="student"))
    status = serializers.ChoiceField(choices=AttendanceRecord.Status.choices)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)


class AttendanceSessionSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    taken_by_name = serializers.CharField(source="taken_by.username", read_only=True)
    records = AttendanceRecordSerializer(many=True, read_only=True)
    summary = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceSession
        fields = (
            "id",
            "group",
            "group_name",
            "course",
            "course_title",
            "taken_by",
            "taken_by_name",
            "session_date",
            "note",
            "records",
            "summary",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "taken_by", "created_at", "updated_at")

    def get_summary(self, obj):
        counters = {
            "attended": 0,
            "attended_online": 0,
            "absent": 0,
            "late": 0,
            "excused": 0,
        }
        for record in obj.records.all():
            counters[record.status] = counters.get(record.status, 0) + 1

        present = counters["attended"] + counters["attended_online"] + counters["late"]
        total = sum(counters.values())
        percentage = round((present / total) * 100, 2) if total else 0
        return {
            "total_marked_students": total,
            "present_students": present,
            "attendance_percentage": percentage,
            "status_breakdown": counters,
        }


class AttendanceSessionWriteSerializer(serializers.ModelSerializer):
    records = AttendanceRecordWriteSerializer(many=True, required=False)
    auto_mark_absent = serializers.BooleanField(required=False, default=True, write_only=True)

    class Meta:
        model = AttendanceSession
        fields = (
            "group",
            "course",
            "session_date",
            "note",
            "records",
            "auto_mark_absent",
        )

    def validate(self, attrs):
        group = attrs.get("group") or getattr(self.instance, "group", None)
        course = attrs.get("course", getattr(self.instance, "course", None))
        records = attrs.get("records")

        if course and group and not group.courses.filter(pk=course.pk).exists():
            raise serializers.ValidationError(
                {"course": "This course is not assigned to the selected group."}
            )

        if records is not None and group:
            group_student_ids = set(
                group.students.filter(role="student").values_list("id", flat=True)
            )
            provided_student_ids = set()
            for record in records:
                student_id = record["student"].id
                if student_id in provided_student_ids:
                    raise serializers.ValidationError(
                        {"records": "Duplicate students are not allowed."}
                    )
                provided_student_ids.add(student_id)
                if student_id not in group_student_ids:
                    raise serializers.ValidationError(
                        {"records": "All students must belong to the selected group."}
                    )
        return attrs

    def _save_records(self, session, records, auto_mark_absent):
        group_students = list(session.group.students.filter(role="student"))
        student_by_id = {student.id: student for student in group_students}
        provided_by_id = {record["student"].id: record for record in records}

        entries = []
        for student_id, record in provided_by_id.items():
            entries.append(
                AttendanceRecord(
                    session=session,
                    student=student_by_id[student_id],
                    status=record["status"],
                    note=record.get("note", ""),
                )
            )

        if auto_mark_absent:
            missing_student_ids = set(student_by_id.keys()) - set(provided_by_id.keys())
            for student_id in missing_student_ids:
                entries.append(
                    AttendanceRecord(
                        session=session,
                        student=student_by_id[student_id],
                        status=AttendanceRecord.Status.ABSENT,
                    )
                )

        session.records.all().delete()
        if entries:
            AttendanceRecord.objects.bulk_create(entries)

    @transaction.atomic
    def create(self, validated_data):
        records = validated_data.pop("records", [])
        auto_mark_absent = validated_data.pop("auto_mark_absent", True)
        validated_data["taken_by"] = self.context["request"].user
        session = AttendanceSession.objects.create(**validated_data)
        self._save_records(session, records, auto_mark_absent)
        return session

    @transaction.atomic
    def update(self, instance, validated_data):
        records = validated_data.pop("records", None)
        auto_mark_absent = validated_data.pop("auto_mark_absent", True)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if records is not None:
            self._save_records(instance, records, auto_mark_absent)
        return instance
