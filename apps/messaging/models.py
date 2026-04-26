from django.conf import settings
from django.db import models
from django.db.models import F, Q

class DirectConversation(models.Model):
    user_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="direct_conversations_as_a",
    )
    user_b = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="direct_conversations_as_b",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "direct_conversations"
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["user_a", "user_b"], name="unique_direct_pair"),
            models.CheckConstraint(condition=~Q(user_a=F("user_b")), name="direct_users_must_differ"),
        ]

    def save(self, *args, **kwargs):
        if self.user_a_id and self.user_b_id and self.user_a_id > self.user_b_id:
            self.user_a_id, self.user_b_id = self.user_b_id, self.user_a_id
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.user_a.username} <> {self.user_b.username}"

class DirectMessage(models.Model):
    conversation = models.ForeignKey(
        DirectConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_direct_messages",
    )
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "direct_messages"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.sender.username}: {self.body[:40]}"

class GroupConversation(models.Model):
    group = models.OneToOneField(
        "groups.Group",
        on_delete=models.CASCADE,
        related_name="conversation",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "group_conversations"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"Group Chat: {self.group.name}"

class GroupMessage(models.Model):
    conversation = models.ForeignKey(
        GroupConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_group_messages",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "group_messages"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.sender.username}@{self.conversation.group.name}: {self.body[:40]}"

class MessageReadReceipt(models.Model):
    """Track which users have read which group messages"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="message_read_receipts",
    )
    group_message = models.ForeignKey(
        GroupMessage,
        on_delete=models.CASCADE,
        related_name="read_receipts",
        null=True,
        blank=True,
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "message_read_receipts"
        unique_together = [["user", "group_message"]]
