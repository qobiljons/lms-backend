from django.db import migrations, models
from django.utils.text import slugify


def populate_slugs(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    for course in Course.objects.all():
        course.slug = slugify(course.title)
        course.save(update_fields=["slug"])


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0003_course_logo"),
    ]

    operations = [
                                                                                         
        migrations.AddField(
            model_name="course",
            name="slug",
            field=models.CharField(max_length=255, default="", blank=True),
            preserve_default=False,
        ),
                                            
        migrations.RunPython(populate_slugs, migrations.RunPython.noop),
                                                             
        migrations.AlterField(
            model_name="course",
            name="slug",
            field=models.SlugField(max_length=255, unique=True, blank=True),
        ),
    ]
