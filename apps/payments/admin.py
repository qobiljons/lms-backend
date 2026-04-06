from django.contrib import admin

from .models import Payment, CoursePurchase

admin.site.register(Payment)
admin.site.register(CoursePurchase)
