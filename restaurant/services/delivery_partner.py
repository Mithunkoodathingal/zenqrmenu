# restaurants/services/delivery_partner.py

from datetime import timedelta

from django.utils import timezone

from restaurant.models import DeliveryPartner, Order

from django.db import transaction



#                           # =============================================================================
                            # =============================================================================

                            # ----------------------------- DELIVERY PARTNER HELPERS ---------------------

                            # =============================================================================
#                           # =============================================================================


# =============================================================================
# Assign Delivery Partner
# =============================================================================

@transaction.atomic
def assign_delivery_partner(
    order: Order,
    partner: DeliveryPartner,
):
    """
    Assign a delivery partner to an order.

    Parameters
    ----------
    order : Order

    partner : DeliveryPartner

    Returns
    -------
    Order
    """

    if order.order_type != "delivery":
        raise ValueError(
            "Only delivery orders can be assigned."
        )

    if order.delivery_partner:
        raise ValueError(
            "Delivery partner already assigned."
        )

    if not partner.is_active:
        raise ValueError(
            "Delivery partner is inactive."
        )

    if not partner.is_available:
        raise ValueError(
            "Delivery partner is unavailable."
        )

    order.delivery_partner = partner

    order.delivery_status = "assigned"

    order.assigned_at = timezone.now()

    order.save(
        update_fields=[
            "delivery_partner",
            "delivery_status",
            "assigned_at",
        ]
    )

    partner.is_available = False

    partner.save(
        update_fields=[
            "is_available",
        ]
    )

    return order

# =============================================================================
# Unassign Delivery Partner
# =============================================================================

@transaction.atomic
def unassign_delivery_partner(
    order: Order,
):
    """
    Remove a delivery partner from an order.

    Parameters
    ----------
    order : Order

    Returns
    -------
    Order
    """

    if order.delivery_partner is None:
        raise ValueError(
            "No delivery partner assigned."
        )

    if order.delivery_status == "delivered":
        raise ValueError(
            "Delivered orders cannot be unassigned."
        )

    partner = order.delivery_partner

    partner.is_available = True

    partner.save(
        update_fields=[
            "is_available",
        ]
    )

    order.delivery_partner = None

    order.delivery_status = "not_required"

    order.assigned_at = None

    order.picked_at = None

    order.delivered_at = None

    order.save(
        update_fields=[
            "delivery_partner",
            "delivery_status",
            "assigned_at",
            "picked_at",
            "delivered_at",
        ]
    )

    return order

# =============================================================================
# Update Delivery Status
# =============================================================================

@transaction.atomic
def update_delivery_status(
    order: Order,
    status: str,
):
    """
    Update delivery status.

    Valid transitions:

        assigned
            ↓

        picked
            ↓

        out_for_delivery
            ↓

        delivered

    Returns
    -------
    Order
    """

    valid_statuses = [

        "pending",

        "assigned",

        "picked",

        "out_for_delivery",

        "delivered",

        "failed",

        "cancelled",

    ]

    if status not in valid_statuses:

        raise ValueError(
            "Invalid delivery status."
        )

    order.delivery_status = status

    now = timezone.now()

    if status == "assigned":

        order.assigned_at = now

    elif status == "picked":

        order.picked_at = now

    elif status == "delivered":

        order.delivered_at = now

        if order.delivery_partner:

            partner = order.delivery_partner

            partner.is_available = True

            partner.total_deliveries += 1

            partner.save(
                update_fields=[
                    "is_available",
                    "total_deliveries",
                ]
            )

    order.save()

    return order

# =============================================================================
# Update Partner Location
# =============================================================================

@transaction.atomic
def update_partner_location(
    partner: DeliveryPartner,
    latitude,
    longitude,
):
    """
    Update live GPS coordinates
    of a delivery partner.
    """

    latitude = float(latitude)

    longitude = float(longitude)

    if latitude < -90 or latitude > 90:
        raise ValueError(
            "Latitude must be between -90 and 90."
        )

    if longitude < -180 or longitude > 180:
        raise ValueError(
            "Longitude must be between -180 and 180."
        )

    partner.current_latitude = latitude

    partner.current_longitude = longitude

    partner.save(
        update_fields=[
            "current_latitude",
            "current_longitude",
        ]
    )

    return partner

# =============================================================================
# Get Delivery Tracking
# =============================================================================

def get_delivery_tracking(
    order: Order,
):
    """
    Return delivery tracking information
    for an order.

    This helper is intentionally independent
    of DRF serializers so it can be reused by:

    • Customer Tracking API
    • Restaurant Dashboard
    • Delivery Partner App
    • Admin Dashboard
    • Notifications
    """

    partner = order.delivery_partner

    # ==========================================================
    # Delivery Partner
    # ==========================================================

    partner_data = None

    if partner:

        partner_data = {

            "id": partner.id,

            "name": (
                f"{partner.first_name} {partner.last_name}".strip()
            ),

            "full_name": partner.full_name,

            "phone": partner.phone,

            "photo": (
                
                partner.profile_photo.url
                
                if partner.profile_photo
                
                else None
                
            ),

            "vehicle_type": partner.vehicle_type,

            "vehicle_number": partner.vehicle_number,

            "rating": float(
                partner.average_rating or 0
            ),

            "completed_orders": (
                partner.total_deliveries
            ),

            "successful_deliveries": (
                partner.successful_deliveries
            ),

            "cancelled_deliveries": (
                partner.cancelled_deliveries
            ),

            "is_available": (
                partner.is_available
            ),

            "is_active": (
                partner.is_active
            ),

            "current_location": {

                "latitude": (
                    float(partner.current_latitude)
                    if partner.current_latitude is not None
                    else None
                ),

                "longitude": (
                    float(partner.current_longitude)
                    if partner.current_longitude is not None
                    else None
                ),

            },

        }

    # ==========================================================
    # ETA
    # ==========================================================

    eta = None

    if order.delivered_at:

        eta = order.delivered_at

    elif order.picked_at:

        eta = (
            order.picked_at
            + timezone.timedelta(minutes=20)
        )

    elif order.assigned_at:

        eta = (
            order.assigned_at
            + timedelta(
                minutes=order.restaurant.average_preparation_time
            )
            + timedelta(
                minutes=int(float(order.delivery_distance_km) * 3)
            )
        )

    # ==========================================================
    # Response
    # ==========================================================

    return {

        "order_id": order.id,

        "order_number": order.order_number,

        "order_status": order.status,

        "delivery_status": order.delivery_status,

        "delivery_partner": partner_data,

        "assigned_at": order.assigned_at,

        "picked_at": order.picked_at,

        "delivered_at": order.delivered_at,

        "estimated_delivery_time": eta,

        "delivery_distance_km": (
            float(order.delivery_distance_km)
            if order.delivery_distance_km is not None
            else None
        ),

        "delivery_charge": (
            float(order.delivery_charge)
            if order.delivery_charge is not None
            else None
        ),

        "customer_location": {

            "latitude": (
                float(order.delivery_latitude)
                if order.delivery_latitude is not None
                else None
            ),

            "longitude": (
                float(order.delivery_longitude)
                if order.delivery_longitude is not None
                else None
            ),

            "address": order.delivery_address,

            "landmark": order.customer_address,

            "pincode": order.customer_pincode,

        },

    }
     
# =============================================================================
# Update Partner Availability
# =============================================================================

@transaction.atomic
def update_partner_availability(
    partner: DeliveryPartner,
    is_available: bool,
):
    """
    Update the availability status of
    a delivery partner.
    """

    partner.is_available = is_available

    partner.save(
        update_fields=[
            "is_available",
        ]
    )

    return partner

