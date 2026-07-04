"""
==========================================================
restaurant/services.py

Business Logic Layer

Contains reusable helper functions for:

• Distance calculations
• Delivery validation
• Delivery charge calculation
• Restaurant coverage
• Location helpers

Views should remain thin and delegate business logic here.

==========================================================
"""

from decimal import Decimal
from math import radians, sin, cos, sqrt, atan2

from django.core.exceptions import ValidationError


# ==========================================================
# Distance Helpers
# ==========================================================

def calculate_distance(
    latitude1,
    longitude1,
    latitude2,
    longitude2,
):
    """
    Calculate distance between two GPS coordinates.

    Returns
    -------
    Decimal
        Distance in kilometers.
    """

    if None in (
        latitude1,
        longitude1,
        latitude2,
        longitude2,
    ):
        return Decimal("0.00")

    earth_radius = 6371.0

    lat1 = radians(float(latitude1))
    lon1 = radians(float(longitude1))

    lat2 = radians(float(latitude2))
    lon2 = radians(float(longitude2))

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(delta_lon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a),
    )

    distance = earth_radius * c

    return Decimal(str(round(distance, 2)))

# ==========================================================
# Coverage
# ==========================================================

def is_inside_delivery_radius(
    restaurant,
    customer_latitude,
    customer_longitude,
):
    """
    Returns True if the customer lies inside
    the restaurant's delivery radius.
    """

    distance = calculate_distance(

        restaurant.delivery_latitude,

        restaurant.delivery_longitude,

        customer_latitude,

        customer_longitude,

    )

    return (

        distance <= restaurant.maximum_delivery_radius_km,

        distance,

    )
    

# ==========================================================
# Delivery Charges
# ==========================================================

def calculate_delivery_charge(
    restaurant,
    distance,
):
    """
    Calculates delivery charge based on distance.
    """

    if distance <= restaurant.free_delivery_radius_km:

        return Decimal("0.00")

    extra_distance = (

        distance
        - restaurant.free_delivery_radius_km

    )

    return (

        extra_distance
        * restaurant.delivery_charge_per_km

    ).quantize(Decimal("0.01"))
    
    

# ==========================================================
# Delivery Validation
# ==========================================================

def validate_delivery(
    restaurant,
    order,
):
    """
    Validates whether an order
    can be delivered.
    """

    if not restaurant.delivery_enabled:

        raise ValidationError(
            "Delivery is disabled."
        )

    inside, distance = is_inside_delivery_radius(

        restaurant,

        order.delivery_latitude,

        order.delivery_longitude,

    )

    if not inside:

        raise ValidationError(
            "Customer is outside delivery radius."
        )

    if (

        order.total_price_cached
        < restaurant.minimum_delivery_order

    ):

        raise ValidationError(

            "Minimum order amount not reached."

        )

    charge = calculate_delivery_charge(

        restaurant,

        distance,

    )

    return {

        "distance": distance,

        "delivery_charge": charge,

    }
    
    
    
# ==========================================================
# Delivery Time
# ==========================================================

def estimate_delivery_time(
    restaurant,
    distance,
):
    """
    Returns estimated delivery time.

    Uses average speed of 30 km/h.
    """

    average_speed = Decimal("30")

    travel_minutes = (

        distance / average_speed

    ) * Decimal("60")

    total = (

        Decimal(restaurant.average_preparation_time)

        + travel_minutes

    )

    return int(total)



# ==========================================================
# Delivery Summary
# ==========================================================

def get_delivery_summary(
    restaurant,
    latitude,
    longitude,
):
    """
    Returns delivery information
    for a customer location.
    """

    inside, distance = is_inside_delivery_radius(

        restaurant,

        latitude,

        longitude,

    )

    charge = calculate_delivery_charge(

        restaurant,

        distance,

    )

    eta = estimate_delivery_time(

        restaurant,

        distance,

    )

    return {

        "can_deliver": inside,

        "distance_km": distance,

        "delivery_charge": charge,

        "estimated_minutes": eta,

        "free_delivery": (

            charge == Decimal("0.00")

        ),

    }
    
    
    
# ==========================================================
# Nearby Restaurants
# ==========================================================

def nearby_restaurants(
    restaurants,
    latitude,
    longitude,
):
    """
    Filters restaurants capable
    of delivering to the customer.

    Returns a list sorted by distance.
    """

    results = []

    for restaurant in restaurants:

        inside, distance = is_inside_delivery_radius(

            restaurant,

            latitude,

            longitude,

        )

        if inside:

            results.append(

                {

                    "restaurant": restaurant,

                    "distance": distance,

                }

            )

    results.sort(

        key=lambda item: item["distance"]

    )

    return results



