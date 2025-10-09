from django.contrib import admin

# Register your models here.
# subscription/admin.py
from django.contrib import admin
from .models import SubscriptionPlan, Subscription

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'table_limit', 'duration_days')
    list_editable = ('price', 'table_limit', 'duration_days')
    search_fields = ('name',)

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'plan', 'is_active', 'start_date', 'end_date')
    search_fields = ('restaurant__name', 'plan__name')
