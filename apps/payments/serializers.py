from rest_framework import serializers
from .models import CoursePurchase, Payment


class PaymentSerializer(serializers.ModelSerializer):
    user_detail = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = (
            "id",
            "user",
            "user_detail",
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


class CoursePurchaseSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_slug = serializers.CharField(source="course.slug", read_only=True)
    course_price = serializers.DecimalField(source="course.price", max_digits=10, decimal_places=2, read_only=True)
    user_detail = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = CoursePurchase
        fields = (
            "id",
            "user",
            "user_detail",
            "course",
            "course_title",
            "course_slug",
            "course_price",
            "payment",
            "payment_status",
            "amount",
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

    def get_payment_status(self, obj):
        if obj.payment:
            return obj.payment.status
        return "succeeded"                                               
