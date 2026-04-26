from django.conf import settings
from django.db import models

class Payment(models.Model):
    STATUS_CHOICES = [
        ("succeeded", "Succeeded"),
        ("pending", "Pending"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="usd")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - ${self.amount} ({self.status})"

class CoursePurchase(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_purchases",
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="purchases",
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="course_purchases",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "course_purchases"
        unique_together = ("user", "course")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.course.title}"
