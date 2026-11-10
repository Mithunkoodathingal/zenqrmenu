from django.contrib import admin

from .models import Coupon, CouponRedemption


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "restaurant", "discount_type", "value", "used_count", "is_active", "audience")
    list_filter = ("discount_type", "is_active", "audience")
    search_fields = ("code", "restaurant__name")


@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):
    list_display = ("coupon", "order", "email", "discount", "created_at")
