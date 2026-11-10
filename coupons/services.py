"""Coupon rules: who may use a code, when, and how much it takes off. Checkout and the validate endpoint share these."""
from decimal import Decimal

from django.db.models import F, Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from common.geo import money
from restaurants.services import _tz

from .models import Coupon, CouponRedemption


def _fail(msg):
    raise ValidationError({"detail": msg, "code": [msg]})


def find(restaurant, code):
    code = str(code or "").strip().upper()
    return Coupon.objects.filter(restaurant=restaurant, code__iexact=code).first() if code else None


def evaluate(restaurant, code, amount, customer, items=None, now=None):
    """Return (coupon, discount). Raises a 400 with a diner-friendly message when the code can't be used.

    `items` are (unit_price, quantity) pairs; needed for buy-one-get-one.
    """
    coupon = find(restaurant, code)
    if coupon is None or not coupon.is_active:
        _fail("This coupon code isn't valid.")
    if customer is None or not customer.email_verified:
        _fail("Sign in with a verified customer account to use coupons.")
    now = now or timezone.now()
    amount = money(amount)
    if coupon.valid_from and now < coupon.valid_from:
        _fail("This coupon hasn't started yet.")
    if coupon.valid_until and now > coupon.valid_until:
        _fail("This coupon has expired.")
    local_day = (now.astimezone(_tz(restaurant)).weekday() + 1) % 7
    if coupon.applicable_days and local_day not in coupon.applicable_days:
        _fail("This coupon can't be used today.")
    if amount < coupon.minimum_order_amount:
        _fail(f"Add ₹{(coupon.minimum_order_amount - amount):.0f} more to use this coupon.")
    if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
        _fail("This coupon has been fully used.")
    email = customer.email.lower()
    if coupon.audience == Coupon.Audience.SELECTED and email not in [e.lower() for e in coupon.customer_emails]:
        _fail("This offer isn't available on your account.")
    if coupon.per_user_limit is not None:
        used = CouponRedemption.objects.filter(coupon=coupon, email__iexact=email).count()
        if used >= coupon.per_user_limit:
            _fail("You've already used this coupon.")
    if coupon.discount_type == Coupon.Type.PERCENT:
        discount = amount * coupon.value / Decimal(100)
    elif coupon.discount_type == Coupon.Type.FIXED:
        discount = coupon.value
    else:
        items = [(money(p), int(q)) for p, q in (items or []) if int(q) > 0]
        if sum(q for _, q in items) < 2:
            _fail("Add at least two items to use this buy-one-get-one offer.")
        discount = min(p for p, _ in items)
    if coupon.maximum_discount:
        discount = min(discount, coupon.maximum_discount)
    return coupon, money(min(discount, amount))


def redeem(coupon, order, discount):
    """Count one use. Locks the coupon row so two diners can't both take the last use."""
    locked = Coupon.objects.select_for_update().get(pk=coupon.pk)
    if locked.usage_limit is not None and locked.used_count >= locked.usage_limit:
        _fail("This coupon has been fully used.")
    Coupon.objects.filter(pk=coupon.pk).update(used_count=F("used_count") + 1)
    CouponRedemption.objects.create(coupon=coupon, order=order, email=order.customer_email.lower(), discount=discount)


def release(order):
    """Give the use back when an order is cancelled."""
    r = CouponRedemption.objects.filter(order=order).first()
    if r:
        Coupon.objects.filter(pk=r.coupon_id, used_count__gt=0).update(used_count=F("used_count") - 1)
        r.delete()


def _live(restaurant):
    now = timezone.now()
    return Coupon.objects.filter(restaurant=restaurant, is_active=True, show_on_menu=True).filter(
        Q(valid_until__isnull=True) | Q(valid_until__gt=now))


def visible_offers(restaurant, customer):
    """Offers listed on the menu. Signed-out diners only see public ones plus how many are locked."""
    live = list(_live(restaurant))
    email = customer.email.lower() if customer else None

    def for_me(c):
        if c.audience == Coupon.Audience.EVERYONE:
            return True
        if not email:
            return False
        return c.audience == Coupon.Audience.SIGNED_IN or email in [e.lower() for e in c.customer_emails]

    mine = [c for c in live if for_me(c)]
    locked = 0 if email else sum(1 for c in live if c.audience != Coupon.Audience.EVERYONE)
    return {"offers": [{"code": c.code, "description": c.description, "discount_type": c.discount_type, "value": float(c.value),
                        "minimum_order_amount": float(c.minimum_order_amount), "audience": c.audience,
                        "personal": c.audience == Coupon.Audience.SELECTED} for c in mine],
            "locked_count": locked}


def public_offer_labels(restaurant):
    """Short labels for map pins and restaurant cards (public offers only)."""
    labels = []
    for c in _live(restaurant).filter(audience=Coupon.Audience.EVERYONE)[:3]:
        if c.discount_type == Coupon.Type.PERCENT:
            labels.append(f"{c.value:g}% off" + (f" over ₹{c.minimum_order_amount:g}" if c.minimum_order_amount else ""))
        elif c.discount_type == Coupon.Type.FIXED:
            labels.append(f"₹{c.value:g} off" + (f" over ₹{c.minimum_order_amount:g}" if c.minimum_order_amount else ""))
        else:
            labels.append("Buy one get one")
    return labels
