# Manual migration to convert lessons.course_id into a proper FK without a default.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0001_initial"),
        ("lessons", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="lesson",
            old_name="course_id",
            new_name="course",
        ),
        migrations.AlterField(
            model_name="lesson",
            name="course",
            field=models.ForeignKey(
                db_column="course_id",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="lessons",
                to="courses.course",
            ),
        ),
    ]

