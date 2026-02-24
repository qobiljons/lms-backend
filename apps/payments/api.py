import logging
from datetime import timedelta
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

from .models import CoursePurchase, Payment, Subscription, SubscriptionPlan
from .serializers import (
    CoursePurchaseSerializer,
    PaymentSerializer,
    SubscriptionPlanSerializer,
    SubscriptionSerializer,
)

logger = logging.getLogger(__name__)


class PaymentPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


# ─── Admin Endpoints ───────────────────────────────────────────────


class PlanListCreateAPIView(generics.ListCreateAPIView):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def perform_create(self, serializer):
        plan = serializer.save()
        # Create Stripe product + price
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            product = stripe.Product.create(
                name=plan.name,
                description=plan.description or f"{plan.name} subscription",
            )
            price = stripe.Price.create(
                product=product.id,
                unit_amount=int(plan.price * 100),
                currency="usd",
                recurring={"interval": "day", "interval_count": plan.duration_days},
            )
            plan.stripe_product_id = product.id
            plan.stripe_price_id = price.id
            plan.save()
        except Exception as e:
            logger.warning(f"Stripe product/price creation failed: {e}")


class PlanDetailAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def _get_plan(self, plan_id):
        try:
            return SubscriptionPlan.objects.get(pk=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return None

    def get(self, request, plan_id):
        plan = self._get_plan(plan_id)
        if plan is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(SubscriptionPlanSerializer(plan).data)

    def patch(self, request, plan_id):
        plan = self._get_plan(plan_id)
        if plan is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = SubscriptionPlanSerializer(plan, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(SubscriptionPlanSerializer(plan).data)

    def delete(self, request, plan_id):
        plan = self._get_plan(plan_id)
        if plan is None:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        plan.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminTransactionsAPIView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdmin)
    pagination_class = PaymentPagination
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("user__username", "user__first_name", "user__last_name", "user__email")
    ordering_fields = ("created_at", "amount", "status")
    ordering = ("-created_at",)

    def get_queryset(self):
        qs = Payment.objects.select_related("user", "subscription__plan").all()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class AdminSubscriptionsAPIView(generics.ListAPIView):
    serializer_class = SubscriptionSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdmin)
    pagination_class = PaymentPagination

    def get_queryset(self):
        return Subscription.objects.select_related("user", "plan").all()


class RevenueStatsAPIView(APIView):
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
        active_subscriptions = Subscription.objects.filter(status="active").count()
        total_payments = Payment.objects.count()

        return Response({
            "total_revenue": str(total_revenue),
            "monthly_revenue": str(monthly_revenue),
            "active_subscriptions": active_subscriptions,
            "total_payments": total_payments,
        })


# ─── Student Endpoints ─────────────────────────────────────────────


class StudentPlansAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True)
        return Response(SubscriptionPlanSerializer(plans, many=True).data)


class CreateCheckoutSessionAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        plan_id = request.data.get("plan_id")
        if not plan_id:
            return Response({"detail": "plan_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            plan = SubscriptionPlan.objects.get(pk=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({"detail": "Plan not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check if user already has an active subscription
        active_sub = Subscription.objects.filter(user=request.user, status="active").first()
        if active_sub:
            return Response(
                {"detail": "You already have an active subscription."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Demo mode: no Stripe keys configured ──
        if not settings.STRIPE_SECRET_KEY or not plan.stripe_price_id:
            now = timezone.now()
            subscription = Subscription.objects.create(
                user=request.user,
                plan=plan,
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=plan.duration_days),
            )
            Payment.objects.create(
                user=request.user,
                subscription=subscription,
                amount=plan.price,
                currency="usd",
                status="succeeded",
                stripe_checkout_session_id=f"demo_{now.timestamp()}",
            )
            return Response({"demo": True, "subscription": SubscriptionSerializer(subscription).data})

        # ── Live Stripe checkout ──
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173") + "/billing"

            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
                mode="subscription",
                success_url=f"{frontend_url}?success=true&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{frontend_url}?cancelled=true",
                client_reference_id=str(request.user.id),
                metadata={
                    "plan_id": str(plan.id),
                    "user_id": str(request.user.id),
                },
            )

            # Create pending payment record
            Payment.objects.create(
                user=request.user,
                amount=plan.price,
                currency="usd",
                status="pending",
                stripe_checkout_session_id=checkout_session.id,
            )

            return Response({"checkout_url": checkout_session.url})
        except Exception as e:
            logger.error(f"Stripe checkout session creation failed: {e}")
            return Response(
                {"detail": "Failed to create checkout session."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CheckoutSuccessAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response({"detail": "session_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            session = stripe.checkout.Session.retrieve(session_id)

            if session.payment_status == "paid":
                plan_id = session.metadata.get("plan_id")
                plan = SubscriptionPlan.objects.get(pk=plan_id)
                now = timezone.now()

                # Create or update subscription
                subscription, created = Subscription.objects.get_or_create(
                    user=request.user,
                    plan=plan,
                    stripe_subscription_id=session.subscription or "",
                    defaults={
                        "status": "active",
                        "current_period_start": now,
                        "current_period_end": now + timedelta(days=plan.duration_days),
                    },
                )

                if not created:
                    subscription.status = "active"
                    subscription.current_period_start = now
                    subscription.current_period_end = now + timedelta(days=plan.duration_days)
                    subscription.save()

                # Update payment record
                payment = Payment.objects.filter(
                    stripe_checkout_session_id=session_id,
                    user=request.user,
                ).first()
                if payment:
                    payment.status = "succeeded"
                    payment.subscription = subscription
                    if session.payment_intent:
                        payment.stripe_payment_intent_id = session.payment_intent
                    payment.save()

                return Response({
                    "status": "success",
                    "subscription": SubscriptionSerializer(subscription).data,
                })

            return Response({"status": "pending", "detail": "Payment not yet confirmed."})
        except Exception as e:
            logger.error(f"Checkout verification failed: {e}")
            return Response(
                {"detail": "Failed to verify checkout session."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MySubscriptionAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        subscription = (
            Subscription.objects.filter(user=request.user)
            .select_related("plan")
            .order_by("-created_at")
            .first()
        )
        if not subscription:
            return Response({"detail": "No subscription found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(SubscriptionSerializer(subscription).data)


class MyPaymentsAPIView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = PaymentPagination

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).select_related("subscription__plan")


# ─── Course Purchase Endpoints ─────────────────────────────────────


class CoursePurchaseCheckoutAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        course_id = request.data.get("course_id")
        if not course_id:
            return Response({"detail": "course_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            return Response({"detail": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

        if course.price == 0:
            return Response({"detail": "This course is free."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if already purchased
        if CoursePurchase.objects.filter(user=request.user, course=course).exists():
            return Response({"detail": "You already own this course."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if user has VIP subscription
        has_vip = Subscription.objects.filter(
            user=request.user, status="active", plan__is_vip=True
        ).exists()
        if has_vip:
            return Response(
                {"detail": "You have VIP access to all courses."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Demo mode ──
        if not settings.STRIPE_SECRET_KEY:
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

        # ── Live Stripe checkout (one-time payment) ──
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")

            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": course.title,
                            "description": course.description[:500] if course.description else f"Access to {course.title}",
                        },
                        "unit_amount": int(course.price * 100),
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=f"{frontend_url}/courses/{course.slug}?purchase_success=true&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{frontend_url}/courses/{course.slug}?cancelled=true",
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
                stripe_checkout_session_id=checkout_session.id,
            )

            return Response({"checkout_url": checkout_session.url})
        except Exception as e:
            logger.error(f"Course purchase checkout failed: {e}")
            return Response(
                {"detail": "Failed to create checkout session."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CoursePurchaseSuccessAPIView(APIView):
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

                # Create purchase if not exists
                purchase, created = CoursePurchase.objects.get_or_create(
                    user=request.user,
                    course=course,
                    defaults={"amount": course.price},
                )

                # Update payment record
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
                {"detail": "Failed to verify checkout session."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MyCoursePurchasesAPIView(generics.ListAPIView):
    serializer_class = CoursePurchaseSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return CoursePurchase.objects.filter(user=self.request.user).select_related("course")


# ─── Stripe Webhook ────────────────────────────────────────────────


class StripeWebhookAPIView(APIView):
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

        event_type = event["type"]
        data = event["data"]["object"]

        if event_type == "checkout.session.completed":
            self._handle_checkout_completed(data)
        elif event_type == "invoice.paid":
            self._handle_invoice_paid(data)
        elif event_type == "invoice.payment_failed":
            self._handle_payment_failed(data)
        elif event_type == "customer.subscription.deleted":
            self._handle_subscription_deleted(data)

        return Response({"status": "ok"})

    def _handle_checkout_completed(self, session):
        metadata = session.get("metadata", {})
        checkout_type = metadata.get("type", "")
        user_id = metadata.get("user_id")

        if not user_id:
            return

        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return

        if checkout_type == "course_purchase":
            # Handle course purchase
            course_id = metadata.get("course_id")
            if not course_id:
                return
            try:
                course = Course.objects.get(pk=course_id)
            except Course.DoesNotExist:
                return

            payment = Payment.objects.filter(
                stripe_checkout_session_id=session["id"],
            ).first()
            if payment:
                payment.status = "succeeded"
                payment.save()

            CoursePurchase.objects.get_or_create(
                user=user,
                course=course,
                defaults={"amount": course.price, "payment": payment},
            )
        else:
            # Handle subscription purchase
            plan_id = metadata.get("plan_id")
            if not plan_id:
                return
            try:
                plan = SubscriptionPlan.objects.get(pk=plan_id)
            except SubscriptionPlan.DoesNotExist:
                return

            now = timezone.now()
            subscription, _ = Subscription.objects.get_or_create(
                user=user,
                stripe_subscription_id=session.get("subscription", ""),
                defaults={
                    "plan": plan,
                    "status": "active",
                    "current_period_start": now,
                    "current_period_end": now + timedelta(days=plan.duration_days),
                },
            )

            Payment.objects.filter(
                stripe_checkout_session_id=session["id"],
            ).update(status="succeeded", subscription=subscription)

    def _handle_invoice_paid(self, invoice):
        sub_id = invoice.get("subscription")
        if not sub_id:
            return
        Subscription.objects.filter(stripe_subscription_id=sub_id).update(status="active")

    def _handle_payment_failed(self, invoice):
        sub_id = invoice.get("subscription")
        if not sub_id:
            return
        Subscription.objects.filter(stripe_subscription_id=sub_id).update(status="past_due")

    def _handle_subscription_deleted(self, subscription_data):
        sub_id = subscription_data.get("id")
        if not sub_id:
            return
        Subscription.objects.filter(stripe_subscription_id=sub_id).update(status="cancelled")
