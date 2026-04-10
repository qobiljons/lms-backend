                                               

from django.db import migrations, models


def populate_usernames(apps, schema_editor):
    User = apps.get_model("users", "User")
    existing = set(
        User.objects.exclude(username__isnull=True)
        .exclude(username="")
        .values_list("username", flat=True)
    )

    for user in User.objects.filter(models.Q(username__isnull=True) | models.Q(username="")):
        base = (user.email.split("@")[0] if user.email else "user").strip() or "user"
        candidate = base
        counter = 1
        while candidate in existing:
            counter += 1
            candidate = f"{base}{counter}"
        user.username = candidate
        user.save(update_fields=["username"])
        existing.add(candidate)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_userprofile_avatar_userprofile_bio_userprofile_phone"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="username",
            field=models.CharField(blank=True, max_length=150, null=True, unique=True),
        ),
        migrations.RunPython(populate_usernames, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="username",
            field=models.CharField(max_length=150, unique=True),
        ),
    ]
