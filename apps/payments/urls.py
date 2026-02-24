from django.urls import path

from . import api

urlpatterns = [
    # Admin endpoints
    path("plans/", api.PlanListCreateAPIView.as_view(), name="plan_list_create"),
    path("plans/<int:plan_id>/", api.PlanDetailAPIView.as_view(), name="plan_detail"),
    path("transactions/", api.AdminTransactionsAPIView.as_view(), name="admin_transactions"),
    path("subscriptions/", api.AdminSubscriptionsAPIView.as_view(), name="admin_subscriptions"),
    path("stats/", api.RevenueStatsAPIView.as_view(), name="revenue_stats"),
    # Student endpoints
    path("available-plans/", api.StudentPlansAPIView.as_view(), name="available_plans"),
    path("checkout/", api.CreateCheckoutSessionAPIView.as_view(), name="create_checkout"),
    path("checkout/success/", api.CheckoutSuccessAPIView.as_view(), name="checkout_success"),
    path("my-subscription/", api.MySubscriptionAPIView.as_view(), name="my_subscription"),
    path("my-payments/", api.MyPaymentsAPIView.as_view(), name="my_payments"),
    path("my-purchases/", api.MyCoursePurchasesAPIView.as_view(), name="my_purchases"),
    # Course purchase
    path("course-checkout/", api.CoursePurchaseCheckoutAPIView.as_view(), name="course_checkout"),
    path("course-checkout/success/", api.CoursePurchaseSuccessAPIView.as_view(), name="course_checkout_success"),
    # Webhook
    path("webhook/stripe/", api.StripeWebhookAPIView.as_view(), name="stripe_webhook"),
]
