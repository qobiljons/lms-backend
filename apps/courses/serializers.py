from rest_framework import serializers

from .models import Course

class CourseSerializer(serializers.ModelSerializer):
    is_accessible = serializers.SerializerMethodField()
    is_purchased = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ("id", "title", "slug", "description", "price", "logo", "created_at", "is_accessible", "is_purchased")
        read_only_fields = ("id", "slug", "created_at", "is_accessible", "is_purchased")

    def get_is_accessible(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        user = request.user

        if user.role in ("admin", "instructor"):
            return True

        if obj.price == 0:
            return True

        from apps.payments.models import CoursePurchase
        return CoursePurchase.objects.filter(user=user, course=obj).exists()

    def get_is_purchased(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        from apps.payments.models import CoursePurchase
        return CoursePurchase.objects.filter(user=request.user, course=obj).exists()
