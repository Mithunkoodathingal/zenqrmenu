from django.db import models

from restaurants.models import Restaurant

ALL_DAYS = [0, 1, 2, 3, 4, 5, 6]  # 0 = Sunday, as the website counts


def all_days():
    return list(ALL_DAYS)


class Coupon(models.Model):
    class Type(models.TextChoices):
        PERCENT = "percent"
        FIXED = "fixed"
        BOGO = "bogo"  # buy one get one: the cheapest item in the basket is free

    class Audience(models.TextChoices):
        EVERYONE = "everyone"
        SIGNED_IN = "signed_in"
        SELECTED = "selected"

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="coupons")
    code = models.CharField(max_length=20)
    description = models.CharField(max_length=255, blank=True)
    discount_type = models.CharField(max_length=10, choices=Type.choices, default=Type.PERCENT)
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    maximum_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    per_user_limit = models.PositiveIntegerField(null=True, blank=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    applicable_days = models.JSONField(default=all_days)
    is_active = models.BooleanField(default=True)
    show_on_menu = models.BooleanField(default=True)
    audience = models.CharField(max_length=10, choices=Audience.choices, default=Audience.EVERYONE)
    customer_emails = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["restaurant", "code"], name="unique_coupon_code")]

    def __str__(self):
        return self.code


class CouponRedemption(models.Model):
    """One use of a coupon on one order. Removed again if the order is cancelled."""

    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="redemptions")
    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="coupon_redemption")
    email = models.EmailField()
    discount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
