"""Order shapes the website reads: owner dashboard, diner tracking page, table status and diner history."""
from django.apps import apps


def _f(v):
    return float(v) if v is not None else None


def item_out(i):
    return {"id": i.id, "food_item": i.food_item_id, "food_item_id": i.food_item_id, "menu_item_id": i.food_item_id,
            "food_item_name": i.name, "name": i.name, "quantity": i.quantity, "price": float(i.unit_price),
            "unit_price": float(i.unit_price), "base_price": float(i.base_price), "total_price": float(i.line_total),
            "selected_addons": i.addons}


def _extras(o, out):
    for app in ("delivery", "inventory", "payments", "kitchen"):
        if apps.is_installed(app):
            module = __import__(f"{app}.hooks", fromlist=["order_fields"])
            fn = getattr(module, "order_fields", None)
            if fn:
                out.update(fn(o))
    return out


def tracking_status(o):
    """The step shown on the diner's tracking page (the delivery app adds "out_for_delivery")."""
    if o.status == "pending":
        return "received"
    if o.status == "completed":
        return {"delivery": "delivered", "pickup": "picked_up"}.get(o.order_type, "completed")
    return o.status


def order_out(o, full=True):
    """Full detail for the restaurant (and for the diner who placed it)."""
    r = o.restaurant
    items = [item_out(i) for i in o.items.all()]
    out = {
        "id": o.id, "order_number": o.order_number, "restaurant": r.id, "restaurant_name": r.name,
        "restaurant_phone": r.phone, "restaurant_latitude": _f(r.latitude), "restaurant_longitude": _f(r.longitude),
        "branch": o.branch_id, "branch_id": o.branch_id, "branch_name": o.branch.name,
        "table": o.table_id, "table_number": o.table_number, "order_type": o.order_type, "status": o.status,
        "kitchen_status": o.status, "is_completed": o.status == "completed",
        "customer_name": o.customer_name, "customer_address": o.customer_address,
        "delivery_latitude": _f(o.delivery_latitude), "delivery_longitude": _f(o.delivery_longitude),
        "delivery_distance_km": _f(o.delivery_distance_km), "scheduled_time": o.scheduled_time,
        "utensils_needed": o.utensils_needed, "tip_recipient": o.tip_recipient,
        "subtotal": float(o.subtotal), "discount_amount": float(o.discount_amount), "coupon_code": o.coupon_code,
        "online_discount": float(o.online_discount), "tax_amount": float(o.tax_amount),
        "delivery_charge": float(o.delivery_charge), "tip_amount": float(o.tip_amount),
        "total_price": float(o.total), "total_price_cached": float(o.total), "grand_total": float(o.total), "total_amount": float(o.total),
        "payment_method": o.payment_method, "payment_status": o.payment_status,
        "handover_verified": o.handover_verified_at is not None,
        "pickup_verified": o.order_type == "pickup" and o.handover_verified_at is not None,
        "delivery_verified": o.order_type == "delivery" and o.handover_verified_at is not None,
        "created_at": o.created_at, "updated_at": o.updated_at, "completed_at": o.completed_at, "cancelled_at": o.cancelled_at,
        "items": items, "order_items": items,
        "status_history": [{"status": e.status, "created_at": e.created_at} for e in o.events.all()],
        "delivery_partner": None, "stock_state": None, "tracking_status": tracking_status(o),
    }
    if full:
        out.update({"customer_phone": o.customer_phone, "customer_email": o.customer_email, "customer_note": o.customer_note})
    return _extras(o, out)


def public_order_out(o):
    """What anyone holding the order number may see: progress and the bill, not the diner's contact details."""
    out = order_out(o, full=False)
    for k in ("customer_address", "delivery_latitude", "delivery_longitude"):
        out[k] = None
    out["customer_name"] = (o.customer_name or "").split(" ")[0]
    partner = out.get("delivery_partner")
    if isinstance(partner, dict):
        out["delivery_partner"] = {k: partner.get(k) for k in ("id", "name", "photo", "latitude", "longitude", "updated_at")}
    return out


def table_order_out(o):
    return {"id": o.id, "order_number": o.order_number, "table": o.table_id, "table_number": o.table_number,
            "status": o.status, "order_type": o.order_type, "total_price": float(o.total), "created_at": o.created_at,
            "updated_at": o.updated_at, "items": [item_out(i) for i in o.items.all()]}


def customer_order_summary(o):
    can_review, reviewed = False, False
    if apps.is_installed("reviews"):
        from reviews.services import review_state
        can_review, reviewed = review_state(o)
    return {"id": o.id, "order_number": o.order_number, "restaurant_id": o.restaurant_id, "restaurant_name": o.restaurant.name,
            "order_type": o.order_type, "status": o.status, "payment_status": o.payment_status, "total_price": float(o.total),
            "created_at": o.created_at, "completed_at": o.completed_at, "can_review": can_review, "reviewed": reviewed}
