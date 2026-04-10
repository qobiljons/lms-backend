from django.db.models.signals import post_migrate, post_save
from django.db.utils import OperationalError, ProgrammingError
from django.dispatch import receiver

from apps.groups.models import Group

from .models import GroupConversation


@receiver(post_save, sender=Group)
def create_group_conversation(sender, instance, created, **kwargs):
    if created:
        GroupConversation.objects.get_or_create(group=instance)


@receiver(post_migrate, dispatch_uid="messaging_create_missing_group_conversations")
def create_missing_group_conversations(sender, **kwargs):
    try:
        groups = Group.objects.all()
    except (OperationalError, ProgrammingError):
        return

    for group in groups:
        GroupConversation.objects.get_or_create(group=group)
