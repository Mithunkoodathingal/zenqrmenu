"""Called by orders when statuses change."""


def after_status_change(order, old, new):
    from .services import record_cash
    if new == "completed" and order.payment_method == "cash":
        record_cash(order, "system")


def order_fields(order):
    receipt = getattr(order, "receipt", None)
    return {"receipt_number": receipt.invoice_number if receipt else None}
