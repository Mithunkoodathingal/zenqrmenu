# restaurants/services/audit.py

from restaurant.models import AuditLog


# ==========================================================
# Create Audit Log
# ==========================================================

def create_audit_log(
    *,
    restaurant,
    action,
    entity,
    description,
    entity_id=None,
    staff=None,
    request=None,
):
    """
    Create an audit log entry.
    """

    ip_address = None
    user_agent = ""

    if request:

        ip_address = request.META.get(
            "REMOTE_ADDR",
        )

        user_agent = request.META.get(
            "HTTP_USER_AGENT",
            "",
        )

    return AuditLog.objects.create(

        restaurant=restaurant,

        staff=staff,

        action=action,

        entity=entity,

        entity_id=entity_id,

        description=description,

        ip_address=ip_address,

        user_agent=user_agent,

    )

# ==========================================================
# Staff Description Builder
# ==========================================================

def build_staff_description(
    staff,
    action,
):
    """
    Build a standard audit description for staff actions.
    """

    descriptions = {

        AuditLog.Action.STAFF_CREATED:
            f"Staff '{staff.full_name}' was created.",

        AuditLog.Action.STAFF_UPDATED:
            f"Staff '{staff.full_name}' was updated.",

        AuditLog.Action.STAFF_DELETED:
            f"Staff '{staff.full_name}' was deleted.",

        AuditLog.Action.ROLE_CHANGED:
            (
                f"Role changed for "
                f"'{staff.full_name}' "
                f"to '{staff.role}'."
            ),

        AuditLog.Action.SHIFT_STARTED:
            f"Shift started for '{staff.full_name}'.",

        AuditLog.Action.SHIFT_ENDED:
            f"Shift ended for '{staff.full_name}'.",

        AuditLog.Action.CLOCK_IN:
            f"'{staff.full_name}' clocked in.",

        AuditLog.Action.CLOCK_OUT:
            f"'{staff.full_name}' clocked out.",

        AuditLog.Action.BREAK_STARTED:
            f"'{staff.full_name}' started a break.",

        AuditLog.Action.BREAK_ENDED:
            f"'{staff.full_name}' ended a break.",

    }

    return descriptions.get(
        action,
        f"Staff action '{action}' performed.",
    )


# ==========================================================
# Order Description Builder
# ==========================================================

def build_order_description(
    order,
    action,
):
    """
    Build a standard audit description for order actions.
    """

    descriptions = {

        AuditLog.Action.ORDER_CONFIRMED:
            (
                f"Order "
                f"'{order.order_number}' "
                f"was confirmed."
            ),

        AuditLog.Action.ORDER_PREPARING:
            (
                f"Order "
                f"'{order.order_number}' "
                f"is being prepared."
            ),

        AuditLog.Action.ORDER_READY:
            (
                f"Order "
                f"'{order.order_number}' "
                f"is ready."
            ),

        AuditLog.Action.ORDER_SERVED:
            (
                f"Order "
                f"'{order.order_number}' "
                f"was served."
            ),

        AuditLog.Action.PRIORITY_CHANGED:
            (
                f"Priority changed to "
                f"'{order.kitchen_priority}' "
                f"for order "
                f"'{order.order_number}'."
            ),

    }

    return descriptions.get(
        action,
        f"Order action '{action}' performed.",
    )


# ==========================================================
# Delivery Description Builder
# ==========================================================

def build_delivery_description(
    delivery,
    action,
):
    """
    Build a standard audit description for delivery actions.
    """

    descriptions = {

        AuditLog.Action.DELIVERY_ASSIGNED:
            (
                f"Delivery assigned "
                f"for order "
                f"'{delivery.order.order_number}'."
            ),

        AuditLog.Action.DELIVERY_STARTED:
            (
                f"Delivery started "
                f"for order "
                f"'{delivery.order.order_number}'."
            ),

        AuditLog.Action.DELIVERY_COMPLETED:
            (
                f"Delivery completed "
                f"for order "
                f"'{delivery.order.order_number}'."
            ),

        AuditLog.Action.DELIVERY_CANCELLED:
            (
                f"Delivery cancelled "
                f"for order "
                f"'{delivery.order.order_number}'."
            ),

    }

    return descriptions.get(
        action,
        f"Delivery action '{action}' performed.",
    )
    
# ==========================================================
# Kitchen Note Description Builder
# ==========================================================

def build_kitchen_note_description(
    kitchen_note,
    action,
):
    """
    Build a standard audit description for kitchen note actions.
    """

    descriptions = {

        AuditLog.Action.KITCHEN_NOTE_CREATED:
            (
                f"Kitchen note added "
                f"to order "
                f"'{kitchen_note.order.order_number}'."
            ),

        AuditLog.Action.KITCHEN_NOTE_UPDATED:
            (
                f"Kitchen note updated "
                f"for order "
                f"'{kitchen_note.order.order_number}'."
            ),

        AuditLog.Action.KITCHEN_NOTE_ARCHIVED:
            (
                f"Kitchen note archived "
                f"for order "
                f"'{kitchen_note.order.order_number}'."
            ),

    }

    return descriptions.get(
        action,
        f"Kitchen note action '{action}' performed.",
    )


# ==========================================================
# Payment Description Builder
# ==========================================================

def build_payment_description(
    payment,
    action,
):
    """
    Build a standard audit description for payment actions.
    """

    descriptions = {

        AuditLog.Action.PAYMENT_RECEIVED:
            (
                f"Payment of "
                f"{payment.amount} "
                f"received for order "
                f"'{payment.order.order_number}'."
            ),

    }

    return descriptions.get(
        action,
        f"Payment action '{action}' performed.",
    )


# ==========================================================
# Restaurant Description Builder
# ==========================================================

def build_restaurant_description(
    restaurant,
    action,
):
    """
    Build a standard audit description for restaurant actions.
    """

    descriptions = {

        AuditLog.Action.RESTAURANT_UPDATED:
            (
                f"Restaurant "
                f"'{restaurant.name}' "
                f"was updated."
            ),

        AuditLog.Action.SETTINGS_UPDATED:
            (
                f"Settings updated "
                f"for restaurant "
                f"'{restaurant.name}'."
            ),

        AuditLog.Action.SUBSCRIPTION_CHANGED:
            (
                f"Subscription updated "
                f"for restaurant "
                f"'{restaurant.name}'."
            ),

    }

    return descriptions.get(
        action,
        f"Restaurant action '{action}' performed.",
    )

# ==========================================================
# Get Audit Logs
# ==========================================================

def get_audit_logs(
    *,
    restaurant,
    action=None,
    entity=None,
    entity_id=None,
    staff_id=None,
    from_date=None,
    to_date=None,
):
    """
    Return audit logs.
    """

    queryset = AuditLog.objects.filter(
        restaurant=restaurant,
    )

    if action:

        queryset = queryset.filter(
            action=action,
        )

    if entity:

        queryset = queryset.filter(
            entity=entity,
        )

    if entity_id is not None:

        queryset = queryset.filter(
            entity_id=entity_id,
        )

    if staff_id is not None:

        queryset = queryset.filter(
            staff_id=staff_id,
        )

    if from_date:

        queryset = queryset.filter(
            created_at__date__gte=from_date,
        )

    if to_date:

        queryset = queryset.filter(
            created_at__date__lte=to_date,
        )

    return queryset.select_related(

        "restaurant",

        "staff",

    ).order_by(

        "-created_at",

    )
    
    
# =============================================================================
# Restaurant Audit
# =============================================================================

def audit_restaurant(
    *,
    restaurant,
    action,
    staff=None,
    request=None,
):
    """
    Create restaurant audit log.
    """

    return create_audit_log(

        restaurant=restaurant,

        staff=staff,

        request=request,

        action=action,

        entity="restaurant",

        entity_id=restaurant.id,

        description=build_restaurant_description(

            restaurant,

            action,

        ),

    )


# =============================================================================
# Staff Audit
# =============================================================================

def audit_staff(
    *,
    restaurant,
    staff_member,
    action,
    staff=None,
    request=None,
):
    """
    Create staff audit log.
    """

    return create_audit_log(

        restaurant=restaurant,

        staff=staff,

        request=request,

        action=action,

        entity="staff",

        entity_id=staff_member.id,

        description=build_staff_description(

            staff_member,

            action,

        ),

    )


# =============================================================================
# Order Audit
# =============================================================================

def audit_order(
    *,
    order,
    action,
    staff=None,
    request=None,
):
    """
    Create order audit log.
    """

    return create_audit_log(

        restaurant=order.restaurant,

        staff=staff,

        request=request,

        action=action,

        entity="order",

        entity_id=order.id,

        description=build_order_description(

            order,

            action,

        ),

    )


# =============================================================================
# Delivery Audit
# =============================================================================

def audit_delivery(
    *,
    delivery,
    action,
    staff=None,
    request=None,
):
    """
    Create delivery audit log.
    """

    return create_audit_log(

        restaurant=delivery.restaurant,

        staff=staff,

        request=request,

        action=action,

        entity="delivery",

        entity_id=delivery.id,

        description=build_delivery_description(

            delivery,

            action,

        ),

    )


# =============================================================================
# Kitchen Note Audit
# =============================================================================

def audit_kitchen_note(
    *,
    kitchen_note,
    action,
    staff=None,
    request=None,
):
    """
    Create kitchen note audit log.
    """

    return create_audit_log(

        restaurant=kitchen_note.order.restaurant,

        staff=staff,

        request=request,

        action=action,

        entity="kitchen_note",

        entity_id=kitchen_note.id,

        description=build_kitchen_note_description(

            kitchen_note,

            action,

        ),

    )


# =============================================================================
# Payment Audit
# =============================================================================

def audit_payment(
    *,
    payment,
    action,
    staff=None,
    request=None,
):
    """
    Create payment audit log.
    """

    return create_audit_log(

        restaurant=payment.order.restaurant,

        staff=staff,

        request=request,

        action=action,

        entity="payment",

        entity_id=payment.id,

        description=build_payment_description(

            payment,

            action,

        ),

    )


# =============================================================================
# Generic Audit
# =============================================================================

def audit(
    *,
    restaurant,
    action,
    entity,
    entity_id,
    description,
    staff=None,
    request=None,
):
    """
    Generic audit helper for custom events.
    """

    return create_audit_log(

        restaurant=restaurant,

        staff=staff,

        request=request,

        action=action,

        entity=entity,

        entity_id=entity_id,

        description=description,

    )


# =============================================================================
# Recent Audit Logs
# =============================================================================

def get_recent_audit_logs(
    *,
    restaurant,
    limit=25,
):
    """
    Return the most recent audit log entries.
    """

    return (

        AuditLog.objects

        .filter(

            restaurant=restaurant,

        )

        .select_related(

            "restaurant",

            "staff",

        )

        .order_by(

            "-created_at",

        )[:limit]

    )


# =============================================================================
# Audit Log Count
# =============================================================================

def get_audit_log_count(
    *,
    restaurant,
):
    """
    Return the total number of audit log entries.
    """

    return (

        AuditLog.objects

        .filter(

            restaurant=restaurant,

        )

        .count()

    )


# =============================================================================
# Delete Audit Logs
# =============================================================================

def delete_audit_logs(
    *,
    restaurant,
):
    """
    Permanently delete all audit logs for a restaurant.

    Intended for maintenance or GDPR cleanup.
    """

    return (

        AuditLog.objects

        .filter(

            restaurant=restaurant,

        )

        .delete()

    )