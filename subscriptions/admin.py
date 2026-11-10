from django.contrib import admin

from .models import Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "duration_days", "table_limit", "menu_item_limit", "is_active", "position")
    list_editable = ("price", "table_limit", "is_active", "position")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("restaurant", "plan", "status", "started_at", "renews_at")
    list_filter = ("status", "plan")
