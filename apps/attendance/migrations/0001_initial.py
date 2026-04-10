                                               

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('courses', '0005_course_price'),
        ('groups', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AttendanceSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_date', models.DateField()),
                ('note', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('course', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='attendance_sessions', to='courses.course')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance_sessions', to='groups.group')),
                ('taken_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='attendance_taken_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'attendance_sessions',
                'ordering': ['-session_date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AttendanceRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('attended', 'Attended'), ('attended_online', 'Attended Online'), ('absent', 'Absent'), ('late', 'Late'), ('excused', 'Excused')], default='absent', max_length=20)),
                ('note', models.CharField(blank=True, max_length=255)),
                ('marked_at', models.DateTimeField(auto_now=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance_records', to=settings.AUTH_USER_MODEL)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='records', to='attendance.attendancesession')),
            ],
            options={
                'db_table': 'attendance_records',
                'ordering': ['student__username'],
            },
        ),
        migrations.AddConstraint(
            model_name='attendancesession',
            constraint=models.UniqueConstraint(fields=('group', 'course', 'session_date'), name='unique_attendance_group_course_session_date'),
        ),
        migrations.AddConstraint(
            model_name='attendancerecord',
            constraint=models.UniqueConstraint(fields=('session', 'student'), name='unique_attendance_session_student'),
        ),
    ]
