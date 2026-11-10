"""Called by orders when one is placed or changes status."""
from .services import notify

STATUS_EVENTS = {"confirmed": "order_confirmed", "preparing": "order_preparing", "ready": "order_ready"}


def _label(order):
    where = f"table {order.table_number}" if order.order_type == "dinein" and order.table_number else order.order_type
    return f"#{order.order_number} ({where})"


def on_order_created(order):
    notify(order.restaurant, "order_received", f"New order {_label(order)}",
           f"{order.customer_name or 'A guest'} ordered ₹{order.total:.0f}.", order)


def after_status_change(order, old, new):
    if new in STATUS_EVENTS:
        notify(order.restaurant, STATUS_EVENTS[new], f"Order {_label(order)} is {new}", order=order)
    elif new == "completed" and order.order_type == "delivery":
        notify(order.restaurant, "order_delivered", f"Order {_label(order)} was delivered", order=order)


def payment_failed(order, reason=""):
    notify(order.restaurant, "payment_failed", f"Payment failed for order {_label(order)}", reason, order)


def refund_completed(order, amount):
    notify(order.restaurant, "refund_completed", f"Refund of ₹{amount:.0f} completed for order {_label(order)}", order=order)
