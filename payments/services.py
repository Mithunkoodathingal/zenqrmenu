"""Payment rules used by checkout and by the payment screens."""
from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from common.geo import money

from .models import Payment, PaymentAudit, PaymentIncentive, PaymentSettings, Receipt
from .routing import route


def _fail(msg, field="payment_method"):
    raise ValidationError({field: [msg], "detail": msg})


def settings_for(restaurant):
    return PaymentSettings.objects.filter(restaurant=restaurant).first() or PaymentSettings(restaurant=restaurant)


def online_ready(restaurant, branch):
    s = settings_for(restaurant)
    key, secret, _, _ = route(branch)
    return bool(s.is_active and s.accept_online and key and secret)


def check_payment_method(restaurant, branch, order_type, method):
    s = settings_for(restaurant)
    if method == "online":
        if not online_ready(restaurant, branch):
            _fail("Online payment isn't available at this restaurant. Choose cash.")
        return
    if order_type == "pickup" and not s.accept_cash_pickup:
        _fail("This restaurant only takes online payment for pickup.")
    if order_type == "delivery" and not s.accept_cash_delivery:
        _fail("This restaurant only takes online payment for delivery.")


def _types(values):
    return {str(v).replace("_", "").replace("-", "").lower() for v in values or []}


def online_incentive(restaurant, order_type, amount):
    """Discount for paying online, per the owner's settings. 0 when off or not applicable."""
    inc = PaymentIncentive.objects.filter(restaurant=restaurant, enabled=True).first()
    if inc is None or inc.value <= 0:
        return Decimal("0")
    if inc.order_types and order_type not in _types(inc.order_types):
        return Decimal("0")
    if inc.min_order and amount < inc.min_order:
        return Decimal("0")
    off = amount * inc.value / 100 if inc.type == "percent" else inc.value
    if inc.max_discount:
        off = min(off, inc.max_discount)
    return money(max(Decimal("0"), min(off, amount)))


def audit(action, description, payment=None, order=None, user=""):
    PaymentAudit.objects.create(payment=payment, order=order or (payment.order if payment else None),
                                action=action, description=description[:255], user=str(user or "")[:150])


def ensure_receipt(order):
    """One receipt per paid order, numbered per restaurant: INV-<year>-<n>."""
    existing = Receipt.objects.filter(order=order).first()
    if existing:
        return existing
    prefix = (order.restaurant.settings or {}).get("invoice_prefix") or "INV"
    year = timezone.now().year
    with transaction.atomic():
        n = Receipt.objects.filter(order__restaurant=order.restaurant, invoice_number__startswith=f"{prefix}-{year}-").count() + 1
        return Receipt.objects.create(order=order, invoice_number=f"{prefix}-{year}-{n:05d}")


def mark_paid(order, payment, by=""):
    from orders.models import Order
    payment.status = Payment.Status.CAPTURED
    payment.captured_at = payment.captured_at or timezone.now()
    payment.save()
    Order.objects.filter(pk=order.pk).update(payment_status=Order.PaymentStatus.PAID, updated_at=timezone.now())
    order.payment_status = Order.PaymentStatus.PAID
    PaymentSettings.objects.filter(restaurant=order.restaurant).update(last_payment_received_at=timezone.now())
    ensure_receipt(order)
    audit("captured", f"{payment.gateway} payment of ₹{payment.amount} received", payment, user=by)


def record_cash(order, by=""):
    """Cash orders count as paid when they are completed."""
    if order.payments.filter(status=Payment.Status.CAPTURED).exists():
        return
    p = Payment.objects.create(restaurant=order.restaurant, branch=order.branch, order=order, amount=order.total,
                               gateway="cash", method="cash", customer_name=order.customer_name, settlement_status="settled")
    mark_paid(order, p, by)
