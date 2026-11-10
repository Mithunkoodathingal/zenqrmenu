from django.contrib import admin

from .models import Order, OrderEvent, OrderItem


class ItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("name", "base_price", "unit_price", "quantity", "addons")


class EventInline(admin.TabularInline):
    model = OrderEvent
    extra = 0
    readonly_fields = ("status", "note", "created_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "restaurant", "order_type", "status", "total", "payment_method", "payment_status", "created_at")
    list_filter = ("order_type", "status", "payment_method", "payment_status")
    search_fields = ("order_number", "restaurant__name", "customer_email", "customer_phone")
    exclude = ("handover_code_hash",)
    inlines = [ItemInline, EventInline]
