
from datetime import timezone

from django.shortcuts import get_object_or_404

from django.db.models import ExpressionWrapper, F, DurationField, Avg, Sum, DecimalField

from restaurant.models import KitchenNote, Order
from restaurant.services.common import get_order

#                           # =============================================================================
                            # =============================================================================

                            # ---------------------------- KDS HEALPER SERVICES ---------------------------

                            # =============================================================================
#                           # =============================================================================

# ==========================================================
# KDS Services
# ==========================================================

def get_kds_orders(
    *,
    restaurant,
    kitchen_status=None,
    priority=None,
    order_type=None,
):
    """
    Return KDS orders for a restaurant.
    """

    orders = Order.objects.filter(
        restaurant=restaurant,
        is_deleted=False,
    )

    if kitchen_status:
        orders = orders.filter(
            kitchen_status=kitchen_status,
        )

    if priority:
        orders = orders.filter(
            kitchen_priority=priority,
        )

    if order_type:
        orders = orders.filter(
            order_type=order_type,
        )

    return orders.order_by("-created_at")

# ==========================================================
# Update Kitchen Status
# ==========================================================

def update_kds_status(
    *,
    restaurant,
    order_id,
    kitchen_status,
):
    """
    Update kitchen workflow status.
    """

    order = get_object_or_404(
        Order,
        id=order_id,
        restaurant=restaurant,
        is_deleted=False,
    )

    now = timezone.now()

    order.kitchen_status = kitchen_status

    if kitchen_status == "accepted":

        order.accepted_at = now
        order.status = "confirmed"

    elif kitchen_status == "preparing":

        order.kitchen_started_at = now
        order.status = "preparing"

    elif kitchen_status == "ready":

        order.kitchen_ready_at = now

    elif kitchen_status == "served":

        order.served_at = now
        order.status = "completed"
        order.is_completed = True
        order.completed_at = now

    order.save()

    return order

# ==========================================================
# Update Kitchen Priority
# ==========================================================

def update_kds_priority(
    
    *,
    
    restaurant,
    
    order_id,
    
    kitchen_priority,
    
):
    """
    Update order priority.
    """

    order = get_object_or_404(
        
        Order,
        
        id=order_id,
        
        restaurant=restaurant,
        
        is_deleted=False,
        
    )

    order.kitchen_priority = kitchen_priority

    order.save(
        
        update_fields=[
            
            "kitchen_priority",
            
        ]
        
    )

    return order

# ==========================================================
# Create Kitchen Note
# ==========================================================

# def create_kds_note(
#     *,
#     restaurant,
#     order_id,
#     staff,
#     note,
#     note_type="general",
#     is_internal=True,
#     is_pinned=False,
# ):
#     """
#     Create a kitchen note.
#     """

#     order = get_object_or_404(
#         Order,
#         id=order_id,
#         restaurant=restaurant,
#         is_deleted=False,
#     )

#     kitchen_note = KitchenNote.objects.create(
#         order=order,
#         staff=staff,
#         note=note,
#         note_type=note_type,
#         is_internal=is_internal,
#         is_pinned=is_pinned,
#     )

#     return kitchen_note

# ==========================================================
# KDS Statistics
# ==========================================================

def get_kds_statistics(
    *,
    restaurant,
):
    """
    Return Kitchen Dashboard statistics.
    """

    orders = Order.objects.filter(
        restaurant=restaurant,
        is_deleted=False,
    )

    average_preparation = (
        orders.filter(
            kitchen_started_at__isnull=False,
            kitchen_ready_at__isnull=False,
        )
        .annotate(
            prep_time=ExpressionWrapper(
                F("kitchen_ready_at") - F("kitchen_started_at"),
                output_field=DurationField(),
            )
        )
        .aggregate(
            average=Avg("prep_time"),
        )["average"]
    )

    average_minutes = 0

    if average_preparation:
        average_minutes = round(
            average_preparation.total_seconds() / 60,
            2,
        )

    return {

        "pending_orders":
            orders.filter(
                kitchen_status="pending",
            ).count(),

        "accepted_orders":
            orders.filter(
                kitchen_status="accepted",
            ).count(),

        "preparing_orders":
            orders.filter(
                kitchen_status="preparing",
            ).count(),

        "ready_orders":
            orders.filter(
                kitchen_status="ready",
            ).count(),

        "served_orders":
            orders.filter(
                kitchen_status="served",
            ).count(),

        "total_active_orders":
            orders.exclude(
                kitchen_status="served",
            ).count(),

        "high_priority_orders":
            orders.filter(
                kitchen_priority="high",
            ).count(),

        "urgent_priority_orders":
            orders.filter(
                kitchen_priority="urgent",
            ).count(),

        "average_preparation_time":
            average_minutes,
    }
    
# ==========================================================
# Mark Order Confirmed
# ==========================================================

def mark_confirmed(
    *,
    restaurant,
    order_id,
):
    """
    Mark an order as confirmed.
    """

    order = get_order(
        restaurant=restaurant,
        order_id=order_id,
    )

    order.kitchen_status = "confirmed"
    order.status = "confirmed"

    order.save(
        update_fields=[
            "kitchen_status",
            "status",
        ]
    )

    return order

# ==========================================================
# Mark Order Preparing
# ==========================================================

def mark_preparing(
    *,
    restaurant,
    order_id,
):
    """
    Mark an order as preparing.
    """

    order = get_order(
        restaurant=restaurant,
        order_id=order_id,
    )

    order.kitchen_status = "preparing"
    order.status = "preparing"

    order.save(
        update_fields=[
            "kitchen_status",
            "status",
        ]
    )

    return order

# ==========================================================
# Mark Order Ready
# ==========================================================

def mark_ready(
    *,
    restaurant,
    order_id,
):
    """
    Mark an order as ready.
    """

    order = get_order(
        restaurant=restaurant,
        order_id=order_id,
    )

    order.kitchen_status = "ready"

    # Optional: keep overall order status in sync.
    order.status = "completed"

    order.save(
        update_fields=[
            "kitchen_status",
            "status",
        ]
    )

    return order

# ==========================================================
# Mark Order Served
# ==========================================================

def mark_served(
    *,
    restaurant,
    order_id,
):
    """
    Mark an order as served.
    """

    order = get_order(
        restaurant=restaurant,
        order_id=order_id,
    )

    order.kitchen_status = "served"
    order.status = "completed"
    order.is_completed = True

    order.save(
        update_fields=[
            "kitchen_status",
            "status",
            "is_completed",
        ]
    )

    return order

# ==========================================================
# Change Kitchen Priority
# ==========================================================

def change_priority(
    *,
    restaurant,
    order_id,
    kitchen_priority,
):
    """
    Change kitchen priority.
    """

    order = get_order(
        restaurant=restaurant,
        order_id=order_id,
    )

    order.kitchen_priority = kitchen_priority

    order.save(
        update_fields=[
            "kitchen_priority",
        ]
    )

    return order



