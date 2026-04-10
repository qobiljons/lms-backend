                                               

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('lessons', '0003_lesson_homework'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Homework',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(help_text='Homework instructions')),
                ('questions', models.JSONField(default=list, help_text="List of questions in format: [{'question': '...', 'points': 10}]")),
                ('total_points', models.IntegerField(default=100)),
                ('due_date', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_homework', to=settings.AUTH_USER_MODEL)),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='homework_assignments', to='lessons.lesson')),
            ],
            options={
                'db_table': 'homework',
                'ordering': ['-created_at'],
                'unique_together': {('lesson', 'title')},
            },
        ),
        migrations.CreateModel(
            name='HomeworkSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('answers', models.JSONField(default=list, help_text="List of answers in format: [{'question_index': 0, 'answer': '...', 'file': 'url'}]")),
                ('files', models.JSONField(default=list, help_text='List of uploaded file URLs')),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('submitted', 'Submitted'), ('graded', 'Graded'), ('returned', 'Returned')], default='draft', max_length=20)),
                ('score', models.DecimalField(blank=True, decimal_places=2, help_text='Score out of total_points', max_digits=5, null=True)),
                ('feedback', models.TextField(blank=True, help_text='Instructor feedback')),
                ('ai_feedback', models.JSONField(default=dict, help_text="AI-generated feedback in format: {'overall': '...', 'per_question': [...]}")),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('graded_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('graded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='graded_homework', to=settings.AUTH_USER_MODEL)),
                ('homework', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to='homework.homework')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='homework_submissions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'homework_submissions',
                'ordering': ['-created_at'],
                'unique_together': {('homework', 'student')},
            },
        ),
        migrations.CreateModel(
            name='HomeworkFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='homework_files/%Y/%m/%d/')),
                ('filename', models.CharField(max_length=255)),
                ('file_type', models.CharField(max_length=50)),
                ('file_size', models.IntegerField(help_text='File size in bytes')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='uploaded_files', to='homework.homeworksubmission')),
            ],
            options={
                'db_table': 'homework_files',
                'ordering': ['-uploaded_at'],
            },
        ),
    ]
