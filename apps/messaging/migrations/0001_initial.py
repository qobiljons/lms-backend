                                               

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('groups', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DirectConversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_a', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='direct_conversations_as_a', to=settings.AUTH_USER_MODEL)),
                ('user_b', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='direct_conversations_as_b', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'direct_conversations',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='DirectMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='messaging.directconversation')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_direct_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'direct_messages',
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='GroupConversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('group', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='conversation', to='groups.group')),
            ],
            options={
                'db_table': 'group_conversations',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='GroupMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='messaging.groupconversation')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_group_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'group_messages',
                'ordering': ['created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='directconversation',
            constraint=models.UniqueConstraint(fields=('user_a', 'user_b'), name='unique_direct_pair'),
        ),
        migrations.AddConstraint(
            model_name='directconversation',
            constraint=models.CheckConstraint(condition=models.Q(('user_a', models.F('user_b')), _negated=True), name='direct_users_must_differ'),
        ),
    ]
