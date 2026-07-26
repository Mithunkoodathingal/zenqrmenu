# restaurant/services/hooks.py

"""
Extension Hooks

This module contains extension points used throughout the
Restaurant application.

Hooks intentionally contain no business logic.

They provide stable integration points for future features such as:

• Celery tasks
• Email notifications
• SMS / WhatsApp
• Push notifications
• Webhooks
• Analytics events
• Third-party integrations

Rules
-----

• Never modify database state.
• Never contain validation.
• Never contain business rules.
• Safe to call multiple times.
"""


# =============================================================================
# Restaurant Hooks
# =============================================================================

def on_restaurant_created(
    *,
    restaurant,
):
    """
    Called after a restaurant is created.
    """

    pass


def on_restaurant_updated(
    *,
    restaurant,
):
    """
    Called after restaurant details are updated.
    """

    pass


def on_restaurant_deleted(
    *,
    restaurant,
):
    """
    Called after a restaurant is deleted.
    """

    pass


def on_restaurant_settings_updated(
    *,
    restaurant,
):
    """
    Called after restaurant settings change.
    """

    pass


def on_subscription_changed(
    *,
    restaurant,
):
    """
    Called after subscription changes.
    """

    pass


# =============================================================================
# Order Hooks
# =============================================================================

def on_order_created(
    *,
    order,
):
    """
    Called after an order is created.
    """

    pass


def on_order_confirmed(
    *,
    order,
):
    """
    Called after an order is confirmed.
    """

    pass


def on_order_preparing(
    *,
    order,
):
    """
    Called after an order enters preparation.
    """

    pass


def on_order_ready(
    *,
    order,
):
    """
    Called after an order becomes ready.
    """

    pass


def on_order_served(
    *,
    order,
):
    """
    Called after an order is served.
    """

    pass


def on_order_completed(
    *,
    order,
):
    """
    Called after an order is completed.
    """

    pass


def on_order_cancelled(
    *,
    order,
):
    """
    Called after an order is cancelled.
    """

    pass


# =============================================================================
# Payment Hooks
# =============================================================================

def on_payment_received(
    *,
    payment,
):
    """
    Called after payment succeeds.
    """

    pass


def on_payment_refunded(
    *,
    payment,
):
    """
    Called after payment refund.
    """

    pass


# =============================================================================
# Kitchen Hooks
# =============================================================================

def on_kitchen_status_changed(
    *,
    order,
):
    """
    Called after kitchen status changes.
    """

    pass


def on_priority_changed(
    *,
    order,
):
    """
    Called after kitchen priority changes.
    """

    pass


def on_kitchen_note_created(
    *,
    kitchen_note,
):
    """
    Called after a kitchen note is created.
    """

    pass


def on_kitchen_note_updated(
    *,
    kitchen_note,
):
    """
    Called after a kitchen note is updated.
    """

    pass


def on_kitchen_note_archived(
    *,
    kitchen_note,
):
    """
    Called after a kitchen note is archived.
    """

    pass


# =============================================================================
# Delivery Hooks
# =============================================================================

def on_delivery_assigned(
    *,
    delivery,
):
    """
    Called after a delivery partner is assigned.
    """

    pass


def on_delivery_started(
    *,
    delivery,
):
    """
    Called after delivery starts.
    """

    pass


def on_delivery_completed(
    *,
    delivery,
):
    """
    Called after delivery completes.
    """

    pass


def on_delivery_cancelled(
    *,
    delivery,
):
    """
    Called after delivery is cancelled.
    """

    pass


# =============================================================================
# Staff Hooks
# =============================================================================

def on_staff_created(
    *,
    staff,
):
    """
    Called after staff creation.
    """

    pass


def on_staff_updated(
    *,
    staff,
):
    """
    Called after staff update.
    """

    pass


def on_staff_deleted(
    *,
    staff,
):
    """
    Called after staff deletion.
    """

    pass


def on_staff_role_changed(
    *,
    staff,
):
    """
    Called after a role change.
    """

    pass


def on_shift_started(
    *,
    staff,
):
    """
    Called after a shift starts.
    """

    pass


def on_shift_ended(
    *,
    staff,
):
    """
    Called after a shift ends.
    """

    pass


def on_clock_in(
    *,
    staff,
):
    """
    Called after clock in.
    """

    pass


def on_clock_out(
    *,
    staff,
):
    """
    Called after clock out.
    """

    pass


def on_break_started(
    *,
    staff,
):
    """
    Called after break starts.
    """

    pass


def on_break_ended(
    *,
    staff,
):
    """
    Called after break ends.
    """

    pass


# =============================================================================
# Customer Hooks
# =============================================================================

def on_customer_registered(
    *,
    customer,
):
    """
    Called after customer registration.
    """

    pass


def on_customer_profile_updated(
    *,
    customer,
):
    """
    Called after customer profile update.
    """

    pass


# =============================================================================
# Table Hooks
# =============================================================================

def on_table_created(
    *,
    table,
):
    """
    Called after a table is created.
    """

    pass


def on_table_updated(
    *,
    table,
):
    """
    Called after a table is updated.
    """

    pass


def on_table_deleted(
    *,
    table,
):
    """
    Called after a table is deleted.
    """

    pass