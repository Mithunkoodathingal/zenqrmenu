# # restaurants/services/kds.py


# =============================================================================
# restaurant/services/kds.py
# =============================================================================

from django.db import transaction
from django.db.models import (
    Avg,
    DurationField,
    ExpressionWrapper,
    F,
    Prefetch,
)

from django.utils import timezone

from django.shortcuts import get_object_or_404

from rest_framework.exceptions import ValidationError

from restaurant.models import (
    AuditLog,
    KitchenNote,
    Order,
    OrderItem,
)
from restaurant.services.audit import build_order_description, create_audit_log
from restaurant.services.common import get_order

# =============================================================================
# Constants
# =============================================================================

VALID_KITCHEN_STATUSES = [

    "pending",

    "confirmed",

    "preparing",

    "ready",

    "served",

]

VALID_PRIORITIES = [

    "low",

    "normal",

    "high",

    "urgent",

]


# =============================================================================
# Private Helpers
# =============================================================================

def _validate_kitchen_status(
    kitchen_status,
):
    """
    Validate kitchen status.
    """

    if kitchen_status not in VALID_KITCHEN_STATUSES:

        raise ValidationError(
            {
                "kitchen_status":
                    "Invalid kitchen status."
            }
        )


def _validate_priority(
    priority,
):
    """
    Validate kitchen priority.
    """

    if priority not in VALID_PRIORITIES:

        raise ValidationError(
            {
                "kitchen_priority":
                    "Invalid kitchen priority."
            }
        )


def _update_status_timestamp(
    *,
    order,
    kitchen_status,
):
    """
    Update timestamps when
    kitchen status changes.
    """

    now = timezone.now()

    if kitchen_status == "confirmed":

        if order.accepted_at is None:

            order.accepted_at = now

    elif kitchen_status == "preparing":

        if order.kitchen_started_at is None:

            order.kitchen_started_at = now

    elif kitchen_status == "ready":

        if order.kitchen_ready_at is None:

            order.kitchen_ready_at = now

    elif kitchen_status == "served":

        if order.served_at is None:

            order.served_at = now

        if order.completed_at is None:

            order.completed_at = now


# =============================================================================
# Base Queryset
# =============================================================================

def _get_kds_queryset(
    *,
    restaurant,
):
    """
    Optimized queryset used
    throughout the KDS module.
    """

    return (

        Order.objects

        .filter(

            restaurant=restaurant,

            is_deleted=False,

        )

        .select_related(

            "table",

            "delivery_partner",

        )

        .prefetch_related(

            Prefetch(
                "order_items",
                queryset=OrderItem.objects.select_related(
                    "food_item",
                ),
            ),

            Prefetch(
                "kitchen_notes",
                queryset=KitchenNote.objects.filter(
                    is_deleted=False,
                ).order_by(
                    "-is_pinned",
                    "-created_at",
                ),
            ),

        )

        .order_by(

            "kitchen_priority",

            "created_at",

        )

    )


# =============================================================================
# Kitchen Queue
# =============================================================================

def get_kds_orders(
    *,
    restaurant,
    kitchen_status=None,
    priority=None,
    order_type=None,
):
    """
    Return Kitchen Display System queue.

    Optional Filters

    • kitchen_status

    • priority

    • order_type
    """

    queryset = _get_kds_queryset(
        restaurant=restaurant,
    )

    if kitchen_status:

        queryset = queryset.filter(
            kitchen_status=kitchen_status,
        )

    if priority:

        queryset = queryset.filter(
            kitchen_priority=priority,
        )

    if order_type:

        queryset = queryset.filter(
            order_type=order_type,
        )

    return queryset


# =============================================================================
# New Orders
# =============================================================================

def get_new_orders(
    *,
    restaurant,
):
    """
    Orders waiting for kitchen acceptance.
    """

    return get_kds_orders(

        restaurant=restaurant,

        kitchen_status="pending",

    )


# =============================================================================
# Preparing Orders
# =============================================================================

def get_preparing_orders(
    *,
    restaurant,
):
    """
    Orders currently
    being prepared.
    """

    return get_kds_orders(

        restaurant=restaurant,

        kitchen_status="preparing",

    )


# =============================================================================
# Ready Orders
# =============================================================================

def get_ready_orders(
    *,
    restaurant,
):
    """
    Orders ready
    for serving or delivery.
    """

    return get_kds_orders(

        restaurant=restaurant,

        kitchen_status="ready",

    )


# =============================================================================
# Served Orders
# =============================================================================

def get_served_orders(
    *,
    restaurant,
):
    """
    Completed kitchen orders.
    """

    return get_kds_orders(

        restaurant=restaurant,

        kitchen_status="served",

    )
    
    
# ========================================================================================================
# Kitchen Workflow Services
# ========================================================================================================


# =============================================================================
# Update Kitchen Status
# =============================================================================

@transaction.atomic
def update_kds_status(
    *,
    restaurant,
    order_id,
    kitchen_status,
    staff=None,
    request=None,
):
    """
    Update the kitchen workflow status.

    Responsibilities

    • Validate status

    • Update timestamps

    • Synchronize order status

    • Complete order when served

    • Create audit log
    """

    _validate_kitchen_status(
        kitchen_status,
    )

    order = get_order(

        restaurant=restaurant,

        order_id=order_id,

    )

    # ==========================================================
    # Kitchen Status
    # ==========================================================

    order.kitchen_status = kitchen_status

    # ==========================================================
    # Order Status Sync
    # ==========================================================

    if kitchen_status == "pending":

        order.status = "pending"

    elif kitchen_status == "confirmed":

        order.status = "confirmed"

    elif kitchen_status == "preparing":

        order.status = "preparing"

    elif kitchen_status == "ready":

        #
        # Kitchen finished.
        #
        # Front-of-house / delivery
        # will complete the order.
        #

        order.status = "ready"

    elif kitchen_status == "served":

        order.status = "completed"

        order.is_completed = True

    # ==========================================================
    # Timestamps
    # ==========================================================

    _update_status_timestamp(

        order=order,

        kitchen_status=kitchen_status,

    )

    # ==========================================================
    # Save
    # ==========================================================

    order.save()

    # ==========================================================
    # Audit
    # ==========================================================

    action_map = {

        "confirmed":

            AuditLog.Action.ORDER_CONFIRMED,

        "preparing":

            AuditLog.Action.ORDER_PREPARING,

        "ready":

            AuditLog.Action.ORDER_READY,

        "served":

            AuditLog.Action.ORDER_SERVED,

    }

    action = action_map.get(
        kitchen_status,
    )

    if action:

        create_audit_log(

            restaurant=restaurant,

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

    return order


# =============================================================================
# Change Kitchen Priority
# =============================================================================

@transaction.atomic
def change_priority(
    *,
    restaurant,
    order_id,
    kitchen_priority,
    staff=None,
    request=None,
):
    """
    Update kitchen priority.

    Valid priorities

    • low

    • normal

    • high

    • urgent
    """

    _validate_priority(
        kitchen_priority,
    )

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

    create_audit_log(

        restaurant=restaurant,

        staff=staff,

        request=request,

        action=AuditLog.Action.PRIORITY_CHANGED,

        entity="order",

        entity_id=order.id,

        description=build_order_description(

            order,

            AuditLog.Action.PRIORITY_CHANGED,

        ),

    )

    return order


# =============================================================================
# Reopen Kitchen Order
# =============================================================================

@transaction.atomic
def reopen_order(
    *,
    restaurant,
    order_id,
    staff=None,
    request=None,
):
    """
    Reopen a completed kitchen order.

    Useful when food must be remade.
    """

    order = get_order(

        restaurant=restaurant,

        order_id=order_id,

    )

    order.is_completed = False

    order.completed_at = None

    order.served_at = None

    order.kitchen_status = "preparing"

    order.status = "preparing"

    order.save()

    create_audit_log(

        restaurant=restaurant,

        staff=staff,

        request=request,

        action=AuditLog.Action.ORDER_PREPARING,

        entity="order",

        entity_id=order.id,

        description=(

            f"Order "

            f"'{order.order_number}' "

            f"was reopened."

        ),

    )

    return order


# =============================================================================
# Convenience Wrappers
# =============================================================================

# ==========================================================
# Mark Order Confirmed
# ==========================================================

def mark_confirmed(
    *,
    restaurant,
    order_id,
    staff=None,
    request=None,
):
    """
    Mark an order as confirmed.

    Wrapper around update_kds_status().
    """

    return update_kds_status(

        restaurant=restaurant,

        order_id=order_id,

        kitchen_status="confirmed",

        staff=staff,

        request=request,

    )


# ==========================================================
# Mark Order Preparing
# ==========================================================

def mark_preparing(
    *,
    restaurant,
    order_id,
    staff=None,
    request=None,
):
    """
    Mark an order as preparing.

    Wrapper around update_kds_status().
    """

    return update_kds_status(

        restaurant=restaurant,

        order_id=order_id,

        kitchen_status="preparing",

        staff=staff,

        request=request,

    )


# ==========================================================
# Mark Order Ready
# ==========================================================

def mark_ready(
    *,
    restaurant,
    order_id,
    staff=None,
    request=None,
):
    """
    Mark an order as ready.

    Wrapper around update_kds_status().
    """

    return update_kds_status(

        restaurant=restaurant,

        order_id=order_id,

        kitchen_status="ready",

        staff=staff,

        request=request,

    )


# ==========================================================
# Mark Order Served
# ==========================================================

def mark_served(
    *,
    restaurant,
    order_id,
    staff=None,
    request=None,
):
    """
    Mark an order as served.

    Wrapper around update_kds_status().
    """

    return update_kds_status(

        restaurant=restaurant,

        order_id=order_id,

        kitchen_status="served",

        staff=staff,

        request=request,

    )
    
# =============================================================================
# KDS Statistics
# =============================================================================

def get_kds_statistics(
    *,
    restaurant,
):
    """
    Return Kitchen Display System statistics.
    """

    orders = _get_kds_queryset(
        restaurant=restaurant,
    )

    average_preparation = (

        orders

        .filter(

            kitchen_started_at__isnull=False,

            kitchen_ready_at__isnull=False,

        )

        .annotate(

            preparation_time=ExpressionWrapper(

                F("kitchen_ready_at") -
                F("kitchen_started_at"),

                output_field=DurationField(),

            )

        )

        .aggregate(

            average=Avg(
                "preparation_time",
            )

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

        "confirmed_orders":

            orders.filter(
                kitchen_status="confirmed",
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

        "active_orders":

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


# =============================================================================
# Current Kitchen Workload
# =============================================================================

def get_current_workload(
    *,
    restaurant,
):
    """
    Return the current kitchen workload.
    """

    orders = _get_kds_queryset(
        restaurant=restaurant,
    )

    return {

        "pending":

            orders.filter(
                kitchen_status="pending",
            ).count(),

        "confirmed":

            orders.filter(
                kitchen_status="confirmed",
            ).count(),

        "preparing":

            orders.filter(
                kitchen_status="preparing",
            ).count(),

        "ready":

            orders.filter(
                kitchen_status="ready",
            ).count(),

    }


# =============================================================================
# Kitchen Queue Summary
# =============================================================================


def get_queue_summary(
    *,
    restaurant,
):
    """
    Lightweight queue summary.

    Useful for navbar badges,
    polling endpoints, and mobile apps.
    """

    orders = _get_kds_queryset(
        restaurant=restaurant,
    )

    return {

        "pending":

            orders.filter(
                kitchen_status="pending",
            ).count(),

        "confirmed":

            orders.filter(
                kitchen_status="confirmed",
            ).count(),

        "preparing":

            orders.filter(
                kitchen_status="preparing",
            ).count(),

        "ready":

            orders.filter(
                kitchen_status="ready",
            ).count(),

        "served":

            orders.filter(
                kitchen_status="served",
            ).count(),

        "high_priority":

            orders.filter(
                kitchen_priority="high",
            ).count(),

        "urgent_priority":

            orders.filter(
                kitchen_priority="urgent",
            ).count(),

    }


# =============================================================================
# Kitchen Dashboard
# =============================================================================

def get_kds_dashboard(
    *,
    restaurant,
):
    """
    Return complete KDS dashboard payload.
    """

    return {

        "statistics":

            get_kds_statistics(
                restaurant=restaurant,
            ),

        "new_orders":

            get_new_orders(
                restaurant=restaurant,
            ),

        "preparing_orders":

            get_preparing_orders(
                restaurant=restaurant,
            ),

        "ready_orders":

            get_ready_orders(
                restaurant=restaurant,
            ),

        "served_orders":

            get_served_orders(
                restaurant=restaurant,
            ),

        "workload":

            get_current_workload(
                restaurant=restaurant,
            ),

    }


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














# from datetime import timezone

# from django.shortcuts import get_object_or_404

# from django.db.models import ExpressionWrapper, F, DurationField, Avg, Sum, DecimalField

# from restaurant.models import KitchenNote, Order
# from restaurant.services.common import get_order

# #                           # =============================================================================
#                             # =============================================================================

#                             # ---------------------------- KDS HEALPER SERVICES ---------------------------

#                             # =============================================================================
# #                           # =============================================================================

# # ==========================================================
# # KDS Services
# # ==========================================================

# def get_kds_orders(
#     *,
#     restaurant,
#     kitchen_status=None,
#     priority=None,
#     order_type=None,
# ):
#     """
#     Return KDS orders for a restaurant.
#     """

#     orders = Order.objects.filter(
#         restaurant=restaurant,
#         is_deleted=False,
#     )

#     if kitchen_status:
#         orders = orders.filter(
#             kitchen_status=kitchen_status,
#         )

#     if priority:
#         orders = orders.filter(
#             kitchen_priority=priority,
#         )

#     if order_type:
#         orders = orders.filter(
#             order_type=order_type,
#         )

#     return orders.order_by("-created_at")

# # ==========================================================
# # Update Kitchen Status
# # ==========================================================

# def update_kds_status(
#     *,
#     restaurant,
#     order_id,
#     kitchen_status,
# ):
#     """
#     Update kitchen workflow status.
#     """

#     order = get_object_or_404(
#         Order,
#         id=order_id,
#         restaurant=restaurant,
#         is_deleted=False,
#     )

#     now = timezone.now()

#     order.kitchen_status = kitchen_status

#     if kitchen_status == "accepted":

#         order.accepted_at = now
#         order.status = "confirmed"

#     elif kitchen_status == "preparing":

#         order.kitchen_started_at = now
#         order.status = "preparing"

#     elif kitchen_status == "ready":

#         order.kitchen_ready_at = now

#     elif kitchen_status == "served":

#         order.served_at = now
#         order.status = "completed"
#         order.is_completed = True
#         order.completed_at = now

#     order.save()

#     return order

# # ==========================================================
# # Update Kitchen Priority
# # ==========================================================

# def update_kds_priority(
    
#     *,
    
#     restaurant,
    
#     order_id,
    
#     kitchen_priority,
    
# ):
#     """
#     Update order priority.
#     """

#     order = get_object_or_404(
        
#         Order,
        
#         id=order_id,
        
#         restaurant=restaurant,
        
#         is_deleted=False,
        
#     )

#     order.kitchen_priority = kitchen_priority

#     order.save(
        
#         update_fields=[
            
#             "kitchen_priority",
            
#         ]
        
#     )

#     return order

# # ==========================================================
# # Create Kitchen Note
# # ==========================================================

# # def create_kds_note(
# #     *,
# #     restaurant,
# #     order_id,
# #     staff,
# #     note,
# #     note_type="general",
# #     is_internal=True,
# #     is_pinned=False,
# # ):
# #     """
# #     Create a kitchen note.
# #     """

# #     order = get_object_or_404(
# #         Order,
# #         id=order_id,
# #         restaurant=restaurant,
# #         is_deleted=False,
# #     )

# #     kitchen_note = KitchenNote.objects.create(
# #         order=order,
# #         staff=staff,
# #         note=note,
# #         note_type=note_type,
# #         is_internal=is_internal,
# #         is_pinned=is_pinned,
# #     )

# #     return kitchen_note

# # ==========================================================
# # KDS Statistics
# # ==========================================================

# def get_kds_statistics(
#     *,
#     restaurant,
# ):
#     """
#     Return Kitchen Dashboard statistics.
#     """

#     orders = Order.objects.filter(
#         restaurant=restaurant,
#         is_deleted=False,
#     )

#     average_preparation = (
#         orders.filter(
#             kitchen_started_at__isnull=False,
#             kitchen_ready_at__isnull=False,
#         )
#         .annotate(
#             prep_time=ExpressionWrapper(
#                 F("kitchen_ready_at") - F("kitchen_started_at"),
#                 output_field=DurationField(),
#             )
#         )
#         .aggregate(
#             average=Avg("prep_time"),
#         )["average"]
#     )

#     average_minutes = 0

#     if average_preparation:
#         average_minutes = round(
#             average_preparation.total_seconds() / 60,
#             2,
#         )

#     return {

#         "pending_orders":
#             orders.filter(
#                 kitchen_status="pending",
#             ).count(),

#         "accepted_orders":
#             orders.filter(
#                 kitchen_status="accepted",
#             ).count(),

#         "preparing_orders":
#             orders.filter(
#                 kitchen_status="preparing",
#             ).count(),

#         "ready_orders":
#             orders.filter(
#                 kitchen_status="ready",
#             ).count(),

#         "served_orders":
#             orders.filter(
#                 kitchen_status="served",
#             ).count(),

#         "total_active_orders":
#             orders.exclude(
#                 kitchen_status="served",
#             ).count(),

#         "high_priority_orders":
#             orders.filter(
#                 kitchen_priority="high",
#             ).count(),

#         "urgent_priority_orders":
#             orders.filter(
#                 kitchen_priority="urgent",
#             ).count(),

#         "average_preparation_time":
#             average_minutes,
#     }
    
# # ==========================================================
# # Mark Order Confirmed
# # ==========================================================

# def mark_confirmed(
#     *,
#     restaurant,
#     order_id,
# ):
#     """
#     Mark an order as confirmed.
#     """

#     order = get_order(
#         restaurant=restaurant,
#         order_id=order_id,
#     )

#     order.kitchen_status = "confirmed"
#     order.status = "confirmed"

#     order.save(
#         update_fields=[
#             "kitchen_status",
#             "status",
#         ]
#     )

#     return order

# # ==========================================================
# # Mark Order Preparing
# # ==========================================================

# def mark_preparing(
#     *,
#     restaurant,
#     order_id,
# ):
#     """
#     Mark an order as preparing.
#     """

#     order = get_order(
#         restaurant=restaurant,
#         order_id=order_id,
#     )

#     order.kitchen_status = "preparing"
#     order.status = "preparing"

#     order.save(
#         update_fields=[
#             "kitchen_status",
#             "status",
#         ]
#     )

#     return order

# # ==========================================================
# # Mark Order Ready
# # ==========================================================

# def mark_ready(
#     *,
#     restaurant,
#     order_id,
# ):
#     """
#     Mark an order as ready.
#     """

#     order = get_order(
#         restaurant=restaurant,
#         order_id=order_id,
#     )

#     order.kitchen_status = "ready"

#     # Optional: keep overall order status in sync.
#     order.status = "completed"

#     order.save(
#         update_fields=[
#             "kitchen_status",
#             "status",
#         ]
#     )

#     return order

# # ==========================================================
# # Mark Order Served
# # ==========================================================

# def mark_served(
#     *,
#     restaurant,
#     order_id,
# ):
#     """
#     Mark an order as served.
#     """

#     order = get_order(
#         restaurant=restaurant,
#         order_id=order_id,
#     )

#     order.kitchen_status = "served"
#     order.status = "completed"
#     order.is_completed = True

#     order.save(
#         update_fields=[
#             "kitchen_status",
#             "status",
#             "is_completed",
#         ]
#     )

#     return order

# # ==========================================================
# # Change Kitchen Priority
# # ==========================================================

# def change_priority(
#     *,
#     restaurant,
#     order_id,
#     kitchen_priority,
# ):
#     """
#     Change kitchen priority.
#     """

#     order = get_order(
#         restaurant=restaurant,
#         order_id=order_id,
#     )

#     order.kitchen_priority = kitchen_priority

#     order.save(
#         update_fields=[
#             "kitchen_priority",
#         ]
#     )

#     return order



