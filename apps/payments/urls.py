from django.urls import path

from . import api

urlpatterns = [
                                                         
    path("stats/", api.RevenueStatsAPIView.as_view(), name="revenue_stats"),
    path("transactions/", api.AdminTransactionsAPIView.as_view(), name="admin_transactions"),
    path("course-purchases/", api.AdminCoursePurchasesAPIView.as_view(), name="admin_course_purchases"),

                                                          
    path("course-checkout/", api.CoursePurchaseCheckoutAPIView.as_view(), name="course_checkout"),
    path("course-checkout/success/", api.CoursePurchaseSuccessAPIView.as_view(), name="course_checkout_success"),
    path("my-purchases/", api.MyCoursePurchasesAPIView.as_view(), name="my_purchases"),
    path("my-payments/", api.MyPaymentsAPIView.as_view(), name="my_payments"),

                                                          
    path("webhook/stripe/", api.StripeWebhookAPIView.as_view(), name="stripe_webhook"),
]
