                                               

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lessons', '0002_course_fk'),
    ]

    operations = [
        migrations.AddField(
            model_name='lesson',
            name='homework',
            field=models.TextField(blank=True, default=''),
        ),
    ]
