from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import CoursePurchase, Payment, Subscription, SubscriptionPlan

User = get_user_model()


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    subscriber_count = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = (
            "id",
            "name",
            "description",
            "price",
            "duration_days",
            "stripe_price_id",
            "stripe_product_id",
            "is_vip",
            "is_active",
            "subscriber_count",
            "created_at",
        )
        read_only_fields = ("id", "stripe_price_id", "stripe_product_id", "created_at")

    def get_subscriber_count(self, obj):
        return obj.subscriptions.filter(status="active").count()


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_detail = SubscriptionPlanSerializer(source="plan", read_only=True)
    user_detail = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = (
            "id",
            "user",
            "plan",
            "plan_detail",
            "user_detail",
            "status",
            "stripe_subscription_id",
            "current_period_start",
            "current_period_end",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def get_user_detail(self, obj):
        return {
            "id": obj.user.id,
            "username": obj.user.username,
            "email": obj.user.email,
            "first_name": obj.user.first_name,
            "last_name": obj.user.last_name,
        }


class PaymentSerializer(serializers.ModelSerializer):
    user_detail = serializers.SerializerMethodField()
    plan_name = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = (
            "id",
            "user",
            "user_detail",
            "subscription",
            "plan_name",
            "amount",
            "currency",
            "status",
            "stripe_payment_intent_id",
            "stripe_checkout_session_id",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def get_user_detail(self, obj):
        return {
            "id": obj.user.id,
            "username": obj.user.username,
            "email": obj.user.email,
            "first_name": obj.user.first_name,
            "last_name": obj.user.last_name,
        }

    def get_plan_name(self, obj):
        if obj.subscription and obj.subscription.plan:
            return obj.subscription.plan.name
        # Check if it's a course purchase payment
        purchase = obj.course_purchases.first()
        if purchase:
            return f"Course: {purchase.course.title}"
        return None


class CoursePurchaseSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_slug = serializers.CharField(source="course.slug", read_only=True)

    class Meta:
        model = CoursePurchase
        fields = ("id", "user", "course", "course_title", "course_slug", "payment", "amount", "created_at")
        read_only_fields = ("id", "created_at")
