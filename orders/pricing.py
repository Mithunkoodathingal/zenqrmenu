"""Checkout pricing. The server always recomputes the bill; amounts sent by the website are never trusted.

total = subtotal − coupon discount − online-payment discount + tax + delivery charge + tip
"""
from datetime import timedelta
from decimal import Decimal

from django.apps import apps
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError

from common.geo import money, valid_point
from menu.models import FoodItem
from menu.services import BranchMenu
from restaurants.services import delivery_quote, is_open_at, next_open, _tz

from .models import Order

MAX_LINES = 100
MAX_QTY = 50


def _fail(field, msg):
    raise ValidationError({field: [msg], "detail": msg})


def _int(v, field):
    try:
        return int(v)
    except (TypeError, ValueError):
        _fail(field, "Send a whole number.")


def price_lines(restaurant, branch, raw_items):
    """Turn basket lines into priced order lines using this branch's prices and availability."""
    if not isinstance(raw_items, list) or not raw_items:
        _fail("items", "Your basket is empty.")
    if len(raw_items) > MAX_LINES:
        _fail("items", "Too many lines in one order.")
    menu = BranchMenu(restaurant, branch)
    ids = [_int(i.get("food_item_id", i.get("food_item", i.get("id"))) if isinstance(i, dict) else None, "items") for i in raw_items]
    foods = {f.id: f for f in FoodItem.objects.filter(restaurant=restaurant, pk__in=ids).prefetch_related("addons")}
    wanted = {}
    lines = []
    for raw, fid in zip(raw_items, ids):
        food = foods.get(fid)
        if food is None:
            _fail("items", "An item in your basket is no longer on the menu.")
        qty = _int(raw.get("quantity", 1), "quantity")
        if not 1 <= qty <= MAX_QTY:
            _fail("quantity", f"Order between 1 and {MAX_QTY} of {food.name}.")
        reason = menu.unavailable_reason(food)
        if reason:
            _fail("items", f"{food.name} is unavailable: {reason}.")
        wanted[food.id] = wanted.get(food.id, 0) + qty
        left = menu.portions_left(food)
        if left is not None and left < wanted[food.id]:
            _fail("items", f"Only {left} × {food.name} left right now.")
        addon_ids = raw.get("selected_addons_ids") or raw.get("addons") or []
        if not isinstance(addon_ids, list):
            _fail("selected_addons_ids", "Send add-ons as a list.")
        available = {a.id: a for a in food.addons.all() if a.is_available}
        chosen = []
        for aid in addon_ids:
            aid = _int(aid.get("id") if isinstance(aid, dict) else aid, "selected_addons_ids")
            if aid not in available:
                _fail("selected_addons_ids", f"An add-on for {food.name} is no longer available.")
            chosen.append(available[aid])
        base = menu.price(food)
        unit = money(base + sum((a.price for a in chosen), Decimal("0")))
        lines.append({"food": food, "name": food.name, "base_price": base, "unit_price": unit, "quantity": qty,
                      "addons": [{"id": a.id, "name": a.name, "price": float(a.price)} for a in chosen]})
    return lines


def parse_schedule(restaurant, raw, order_type):
    """Scheduled time must be in the future, within a week, and inside opening hours. ASAP needs the restaurant open."""
    now = timezone.now()
    if raw in (None, ""):
        if order_type != Order.Type.DINEIN and not is_open_at(restaurant, now):
            nxt = next_open(restaurant, now)
            when = nxt.astimezone(_tz(restaurant)).strftime("%a %d %b, %I:%M %p") if nxt else None
            _fail("scheduled_time", f"{restaurant.name} is closed right now." + (f" Schedule for {when} or later." if when else ""))
        return None
    when = parse_datetime(str(raw))
    if when is None:
        _fail("scheduled_time", "Pick a valid date and time.")
    if timezone.is_naive(when):
        when = timezone.make_aware(when, _tz(restaurant))
    if when < now + timedelta(minutes=5):
        _fail("scheduled_time", "Pick a time at least a few minutes from now.")
    if when > now + timedelta(days=7):
        _fail("scheduled_time", "You can schedule up to 7 days ahead.")
    if not is_open_at(restaurant, when):
        _fail("scheduled_time", f"{restaurant.name} is closed at that time. Pick another slot.")
    return when


def delivery_details(restaurant, customer, data, subtotal):
    """Address (saved address or typed one with map point), distance and delivery charge."""
    addr_id = data.get("address_id")
    if addr_id not in (None, ""):
        if customer is None:
            _fail("address_id", "Sign in to use a saved address.")
        a = customer.addresses.filter(pk=_int(addr_id, "address_id")).first()
        if a is None:
            _fail("address_id", "That address isn't in your account.")
        if a.latitude is None or a.longitude is None:
            _fail("address_id", "Set this address's location on the map first.")
        address, lat, lng, phone, name = a.one_line(), a.latitude, a.longitude, a.phone, a.recipient_name
    else:
        address = str(data.get("customer_address") or "").strip()
        parts = [data.get(k) for k in ("customer_city", "customer_state", "customer_pincode") if data.get(k)]
        if parts:
            address = ", ".join([address] + [str(p) for p in parts])
        lat, lng = data.get("delivery_latitude"), data.get("delivery_longitude")
        phone, name = "", ""
        if not address:
            _fail("customer_address", "Enter the delivery address.")
        if not valid_point(lat, lng):
            _fail("delivery_latitude", "Pick the delivery location on the map.")
    q = delivery_quote(restaurant, lat, lng, subtotal)
    if not q["inside_area"]:
        _fail("customer_address", f"This address is {q['distance_km']} km away, outside {restaurant.name}'s delivery area.")
    if q["below_minimum"]:
        _fail("items", f"Delivery needs an order of at least ₹{q['minimum_order_amount']:.0f}.")
    return {"customer_address": address, "delivery_latitude": round(Decimal(str(lat)), 6), "delivery_longitude": round(Decimal(str(lng)), 6),
            "delivery_distance_km": Decimal(str(q["distance_km"])), "delivery_charge": money(q["delivery_charge"]),
            "address_phone": phone, "address_name": name}


def tax_for(restaurant, taxable):
    s = restaurant.settings or {}
    if not s.get("tax_enabled"):
        return Decimal("0")
    try:
        pct = Decimal(str(s.get("tax_percentage") or 0))
    except Exception:
        return Decimal("0")
    if pct <= 0 or s.get("prices_include_tax"):
        return Decimal("0")
    return money(taxable * pct / 100)


def price_order(restaurant, branch, order_type, data, customer, payment_method):
    """Everything about the bill. Raises a 400 with a diner-friendly message when something can't be ordered."""
    lines = price_lines(restaurant, branch, data.get("items"))
    subtotal = money(sum((l["unit_price"] * l["quantity"] for l in lines), Decimal("0")))
    bill = {"lines": lines, "subtotal": subtotal, "discount_amount": Decimal("0"), "coupon": None, "coupon_code": "",
            "online_discount": Decimal("0"), "delivery_charge": Decimal("0"), "tip_amount": Decimal("0"), "tip_recipient": ""}

    code = str(data.get("coupon_code") or "").strip()
    if code and apps.is_installed("coupons"):
        from coupons.services import evaluate
        coupon, discount = evaluate(restaurant, code, subtotal, customer, [(l["unit_price"], l["quantity"]) for l in lines])
        bill.update(coupon=coupon, coupon_code=coupon.code, discount_amount=discount)

    after_coupon = subtotal - bill["discount_amount"]
    if apps.is_installed("payments"):
        from payments.services import check_payment_method, online_incentive
        check_payment_method(restaurant, branch, order_type, payment_method)
        if payment_method == Order.PaymentMethod.ONLINE:
            bill["online_discount"] = online_incentive(restaurant, order_type, after_coupon)
    elif payment_method == Order.PaymentMethod.ONLINE:
        _fail("payment_method", "Online payment isn't available at this restaurant.")

    if order_type == Order.Type.DELIVERY:
        bill.update(delivery_details(restaurant, customer, data, subtotal))

    if order_type != Order.Type.DINEIN:
        try:
            tip = money(data.get("tip_amount") or 0)
        except Exception:
            _fail("tip_amount", "Enter a valid tip.")
        if tip < 0:
            _fail("tip_amount", "Tip can't be negative.")
        if tip > max(subtotal, Decimal("100")):
            _fail("tip_amount", "That tip is larger than the order. Please check it.")
        bill["tip_amount"] = tip
        bill["tip_recipient"] = "driver" if order_type == Order.Type.DELIVERY else "restaurant"

    taxable = max(Decimal("0"), after_coupon - bill["online_discount"])
    bill["tax_amount"] = tax_for(restaurant, taxable)
    bill["total"] = money(max(Decimal("0"), taxable + bill["tax_amount"] + bill["delivery_charge"] + bill["tip_amount"]))
    return bill
