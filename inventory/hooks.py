"""Called by orders when statuses change."""
from .services import on_status_change, stock_state  # noqa: F401


def order_fields(order):
    return {"stock_state": stock_state(order)}
