import logging
from decimal import Decimal

import stripe
from django.conf import settings
from django.db.models import Sum
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdmin
from apps.courses.models import Course

from .models import CoursePurchase, Payment
from .serializers import (
    CoursePurchaseSerializer,
    PaymentSerializer,
)

logger = logging.getLogger(__name__)


class PaymentPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


# ─── Admin Endpoints ───────────────────────────────────────────────


class AdminCoursePurchasesAPIView(generics.ListAPIView):
    """Admin: view all course purchases with student details."""
    serializer_class = CoursePurchaseSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdmin)
    pagination_class = PaymentPagination
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("user__username", "user__first_name", "user__last_name", "course__title")
    ordering_fields = ("created_at", "amount")
    ordering = ("-created_at",)

    def get_queryset(self):
        return CoursePurchase.objects.select_related("user", "course", "payment").all()


class AdminTransactionsAPIView(generics.ListAPIView):
    """Admin: view all payment records."""
    serializer_class = PaymentSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdmin)
    pagination_class = PaymentPagination
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("user__username", "user__first_name", "user__last_name", "user__email")
    ordering_fields = ("created_at", "amount", "status")
    ordering = ("-created_at",)

    def get_queryset(self):
        qs = Payment.objects.select_related("user").all()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class RevenueStatsAPIView(APIView):
    """Admin: revenue statistics."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get(self, request):
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total_revenue = (
            Payment.objects.filter(status="succeeded").aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        monthly_revenue = (
            Payment.objects.filter(status="succeeded", created_at__gte=month_start)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        total_payments = Payment.objects.filter(status="succeeded").count()
        total_course_purchases = CoursePurchase.objects.count()

        return Response({
            "total_revenue": str(total_revenue),
            "monthly_revenue": str(monthly_revenue),
            "total_payments": total_payments,
            "total_course_purchases": total_course_purchases,
        })


# ─── Student Course Purchase Endpoints ────────────────────────────


class CoursePurchaseCheckoutAPIView(APIView):
    """Student: initiate payment for a course."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        course_id = request.data.get("course_id")
        if not course_id:
            return Response({"detail": "course_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            return Response({"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

        if float(course.price) == 0:
            return Response({"detail": "This course is free — no payment needed."}, status=status.HTTP_400_BAD_REQUEST)

        # Already purchased?
        if CoursePurchase.objects.filter(user=request.user, course=course).exists():
            return Response({"detail": "You already own this course."}, status=status.HTTP_400_BAD_REQUEST)

        # ── Demo / no Stripe key mode ──
        if not getattr(settings, "STRIPE_SECRET_KEY", None):
            payment = Payment.objects.create(
                user=request.user,
                amount=course.price,
                currency="usd",
                status="succeeded",
                stripe_checkout_session_id=f"demo_course_{timezone.now().timestamp()}",
            )
            purchase = CoursePurchase.objects.create(
                user=request.user,
                course=course,
                payment=payment,
                amount=course.price,
            )
            return Response({
                "demo": True,
                "purchase": CoursePurchaseSerializer(purchase).data,
            })

        # ── Live Stripe one-time checkout ──
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": course.title,
                            "description": (course.description or "")[:500],
                        },
                        "unit_amount": int(course.price * 100),
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=f"{frontend_url}/payments?purchase_success=true&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{frontend_url}/payments?cancelled=true",
                client_reference_id=str(request.user.id),
                metadata={
                    "course_id": str(course.id),
                    "user_id": str(request.user.id),
                    "type": "course_purchase",
                },
            )

            Payment.objects.create(
                user=request.user,
                amount=course.price,
                currency="usd",
                status="pending",
                stripe_checkout_session_id=session.id,
            )

            return Response({"checkout_url": session.url})
        except Exception as e:
            logger.error(f"Stripe course checkout failed: {e}")
            return Response(
                {"detail": "Failed to create checkout session."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CoursePurchaseSuccessAPIView(APIView):
    """Student: verify Stripe payment and unlock course."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response({"detail": "session_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            session = stripe.checkout.Session.retrieve(session_id)

            if session.payment_status == "paid":
                course_id = session.metadata.get("course_id")
                course = Course.objects.get(pk=course_id)

                purchase, _ = CoursePurchase.objects.get_or_create(
                    user=request.user,
                    course=course,
                    defaults={"amount": course.price},
                )

                payment = Payment.objects.filter(
                    stripe_checkout_session_id=session_id,
                    user=request.user,
                ).first()
                if payment:
                    payment.status = "succeeded"
                    if session.payment_intent:
                        payment.stripe_payment_intent_id = session.payment_intent
                    payment.save()
                    purchase.payment = payment
                    purchase.save()

                return Response({
                    "status": "success",
                    "purchase": CoursePurchaseSerializer(purchase).data,
                })

            return Response({"status": "pending", "detail": "Payment not yet confirmed."})
        except Exception as e:
            logger.error(f"Course purchase verification failed: {e}")
            return Response(
                {"detail": "Failed to verify payment."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MyCoursePurchasesAPIView(generics.ListAPIView):
    """Student: list my purchased courses."""
    serializer_class = CoursePurchaseSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return CoursePurchase.objects.filter(user=self.request.user).select_related("course", "payment")


class MyPaymentsAPIView(generics.ListAPIView):
    """Student: list my payment history."""
    serializer_class = PaymentSerializer
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = PaymentPagination

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).order_by("-created_at")


# ─── Stripe Webhook ────────────────────────────────────────────────


class StripeWebhookAPIView(APIView):
    """Handle Stripe events for course purchases."""
    permission_classes = ()
    authentication_classes = ()

    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.warning(f"Webhook signature verification failed: {e}")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if event["type"] == "checkout.session.completed":
            self._handle_checkout_completed(event["data"]["object"])

        return Response({"status": "ok"})

    def _handle_checkout_completed(self, session):
        metadata = session.get("metadata", {})
        if metadata.get("type") != "course_purchase":
            return

        user_id = metadata.get("user_id")
        course_id = metadata.get("course_id")
        if not user_id or not course_id:
            return

        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user = User.objects.get(pk=user_id)
            course = Course.objects.get(pk=course_id)
        except (User.DoesNotExist, Course.DoesNotExist):
            return

        payment = Payment.objects.filter(stripe_checkout_session_id=session["id"]).first()
        if payment:
            payment.status = "succeeded"
            payment.save()

        CoursePurchase.objects.get_or_create(
            user=user,
            course=course,
            defaults={"amount": course.price, "payment": payment},
        )
