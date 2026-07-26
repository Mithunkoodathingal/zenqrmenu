# restaurants/services/quries.py

"""
Read-only query services.

This module contains reusable database queries used throughout
the Restaurant application.

Rules
-----
• No create/update/delete logic.
• No business rules.
• No side effects.
• QuerySets should be optimized with select_related/prefetch_related.
"""


from django.db.models import Q

from math import atan2, cos, radians, sin, sqrt

from django.db.models import Prefetch, QuerySet

from restaurant.models import (
    Category,
    DeliveryPartner,
    FoodItem,
    KitchenNote,
    Order,
    Restaurant,
    Staff,
    Table,
)


# =============================================================================
# Restaurant Queryset
# =============================================================================

def get_restaurant_queryset() -> QuerySet[Restaurant]:
    """
    Base restaurant queryset.
    """

    return (

        Restaurant.objects

        .filter(
            is_deleted=False,
        )

        .select_related(
            "owner",
        )

        .prefetch_related(

            "categories",

            "food_items",

            "tables",

            "staff_members",

            "delivery_partners",

        )

    )


# =============================================================================
# Restaurant
# =============================================================================

def list_restaurants() -> QuerySet[Restaurant]:
    """
    Return all active restaurants.
    """

    return (

        get_restaurant_queryset()

        .filter(
            is_active=True,
        )

        .order_by("name")

    )


# =============================================================================
# List Nearby Restaurants
# =============================================================================

def list_nearby_restaurants(
    *,
    latitude: float,
    longitude: float,
):
    """
    Return restaurants whose delivery radius
    includes the customer's location.
    """

    restaurants = Restaurant.objects.filter(

        is_deleted=False,

        is_active=True,

        delivery_enabled=True,

    )

    nearby_restaurants = []

    for restaurant in restaurants:

        if (

            restaurant.delivery_latitude is None

            or

            restaurant.delivery_longitude is None

        ):

            continue

        distance = calculate_distance(

            latitude,

            longitude,

            restaurant.delivery_latitude,

            restaurant.delivery_longitude,

        )

        if distance <= restaurant.maximum_delivery_radius_km:

            restaurant.distance_km = distance

            nearby_restaurants.append(
                restaurant
            )

    nearby_restaurants.sort(

        key=lambda restaurant: restaurant.distance_km

    )

    return nearby_restaurants

# =============================================================================
# List Restaurants
# =============================================================================


def list_restaurants(
    *,
    filters,
):

    queryset = Restaurant.objects.filter(

        is_deleted=False,

        is_active=True,

    )

    search = filters.get("search")

    if search:

        queryset = queryset.filter(

            Q(name__icontains=search)

            |

            Q(about__icontains=search)

            |

            Q(city__icontains=search)

            |

            Q(cuisine_type__icontains=search)

        )

    if filters.get("city"):

        queryset = queryset.filter(
            city__iexact=filters["city"]
        )

    if filters.get("state"):

        queryset = queryset.filter(
            state__iexact=filters["state"]
        )

    if filters.get("country"):

        queryset = queryset.filter(
            country__iexact=filters["country"]
        )

    if filters.get("cuisine"):

        queryset = queryset.filter(
            cuisine_type__iexact=filters["cuisine"]
        )

    if filters.get("delivery") is not None:

        queryset = queryset.filter(
            delivery_enabled=filters["delivery"]
        )

    if filters.get("pickup") is not None:

        queryset = queryset.filter(
            pickup_enabled=filters["pickup"]
        )

    if filters.get("dine_in") is not None:

        queryset = queryset.filter(
            dine_in_enabled=filters["dine_in"]
        )

    queryset = queryset.order_by(
        filters.get("ordering", "name")
    )

    return queryset


# =============================================================================
# Staff
# =============================================================================

def list_staff(
    *,
    restaurant,
):
    """
    Return restaurant staff.
    """

    return (

        Staff.objects

        .filter(

            restaurant=restaurant,

            is_deleted=False,

        )

        .select_related(
            "user",
        )

        .order_by(

            "first_name",

            "last_name",

        )

    )


# =============================================================================
# Delivery Partners
# =============================================================================

def list_delivery_partners(
    *,
    restaurant,
):
    """
    Return active delivery partners.
    """

    return (

        DeliveryPartner.objects

        .filter(

            restaurant=restaurant,

            is_active=True,

        )

        .order_by(
            "full_name",
        )

    )


# =============================================================================
# Categories
# =============================================================================

def list_categories(
    *,
    restaurant,
):
    """
    Return restaurant categories.
    """

    return (

        Category.objects

        .filter(
            restaurant=restaurant,
        )

        .order_by(

            "display_order",

            "name",

        )

    )


# =============================================================================
# Food Items
# =============================================================================

def list_food_items(
    *,
    restaurant,
):
    """
    Return restaurant menu.
    """

    return (

        FoodItem.objects

        .filter(
            restaurant=restaurant,
        )

        .select_related(
            "category",
        )

        .prefetch_related(
            "addons",
        )

        .order_by(

            "category__display_order",

            "display_order",

            "name",

        )

    )


# =============================================================================
# Available Food Items
# =============================================================================

def list_available_food_items(
    *,
    restaurant,
):
    """
    Return menu items available for ordering.
    """

    return (

        list_food_items(
            restaurant=restaurant,
        )

        .filter(

            is_active=True,

            is_paused=False,

        )

    )


# =============================================================================
# Tables
# =============================================================================

def list_tables(
    *,
    restaurant,
):
    """
    Return restaurant tables.
    """

    return (

        Table.objects

        .filter(
            restaurant=restaurant,
        )

        .order_by(
            "table_number",
        )

    )


# =============================================================================
# Orders
# =============================================================================

def list_orders(
    *,
    restaurant,
):
    """
    Return restaurant orders.
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
            "items",
        )

        .order_by(
            "-created_at",
        )

    )


# =============================================================================
# Active Orders
# =============================================================================

def list_active_orders(
    *,
    restaurant,
):
    """
    Return open orders.
    """

    return (

        list_orders(
            restaurant=restaurant,
        )

        .filter(
            is_completed=False,
        )

    )


# =============================================================================
# Kitchen Notes
# =============================================================================

def list_kitchen_notes(
    *,
    restaurant,
):
    """
    Return kitchen notes.
    """

    return (

        KitchenNote.objects

        .filter(

            order__restaurant=restaurant,

            is_deleted=False,

        )

        .select_related(

            "order",

            "created_by",

        )

        .order_by(
            "-created_at",
        )

    )


# =============================================================================
# Distance Helper
# =============================================================================

def calculate_distance(
    lat1,
    lon1,
    lat2,
    lon2,
):
    """
    Calculate great-circle distance using
    the Haversine formula.
    """

    earth_radius = 6371

    d_lat = radians(
        lat2 - lat1,
    )

    d_lon = radians(
        lon2 - lon1,
    )

    a = (

        sin(d_lat / 2) ** 2

        +

        cos(radians(lat1))

        *

        cos(radians(lat2))

        *

        sin(d_lon / 2) ** 2

    )

    c = 2 * atan2(

        sqrt(a),

        sqrt(1 - a),

    )

    return earth_radius * c


# =============================================================================
# Base Order Queryset
# =============================================================================

def get_order_queryset() -> QuerySet[Order]:
    """
    Base order queryset.
    """

    return (

        Order.objects

        .filter(
            is_deleted=False,
        )

        .select_related(

            "restaurant",

            "table",

            "delivery_partner",

        )

        .prefetch_related(

            "items",

        )

    )


# =============================================================================
# Base Staff Queryset
# =============================================================================

def get_staff_queryset() -> QuerySet[Staff]:
    """
    Base staff queryset.
    """

    return (

        Staff.objects

        .filter(
            is_deleted=False,
        )

        .select_related(

            "restaurant",

            "user",

        )

    )


# =============================================================================
# Base Category Queryset
# =============================================================================

def get_category_queryset() -> QuerySet[Category]:
    """
    Base category queryset.
    """

    return (

        Category.objects

        .select_related(

            "restaurant",

        )

        .order_by(

            "display_order",

            "name",

        )

    )


# =============================================================================
# Base Food Item Queryset
# =============================================================================

def get_food_item_queryset() -> QuerySet[FoodItem]:
    """
    Base food item queryset.
    """

    return (

        FoodItem.objects

        .select_related(

            "restaurant",

            "category",

        )

        .prefetch_related(

            "addons",

        )

        .order_by(

            "category__display_order",

            "display_order",

            "name",

        )

    )


# =============================================================================
# Base Table Queryset
# =============================================================================

def get_table_queryset() -> QuerySet[Table]:
    """
    Base table queryset.
    """

    return (

        Table.objects

        .select_related(

            "restaurant",

        )

        .order_by(

            "table_number",

        )

    )


# =============================================================================
# Base Delivery Partner Queryset
# =============================================================================

def get_delivery_partner_queryset() -> QuerySet[DeliveryPartner]:
    """
    Base delivery partner queryset.
    """

    return (

        DeliveryPartner.objects

        .select_related(

            "restaurant",

        )

        .order_by(

            "full_name",

        )

    )


# =============================================================================
# Base Kitchen Note Queryset
# =============================================================================

def get_kitchen_note_queryset() -> QuerySet[KitchenNote]:
    """
    Base kitchen note queryset.
    """

    return (

        KitchenNote.objects

        .filter(

            is_deleted=False,

        )

        .select_related(

            "order",

            "staff",

            "edited_by",

        )

        .order_by(

            "-is_pinned",

            "-created_at",

        )

    )


# =============================================================================
# Search Restaurants
# =============================================================================

def search_restaurants(
    *,
    keyword,
):
    """
    Search restaurants.
    """

    return (

        list_restaurants()

        .filter(

            Q(name__icontains=keyword)

            |

            Q(description__icontains=keyword)

            |

            Q(address__icontains=keyword)

        )

    )


# =============================================================================
# Filter Restaurants
# =============================================================================

def filter_restaurants(
    *,
    owner=None,
    is_active=None,
):
    """
    Filter restaurants.
    """

    queryset = get_restaurant_queryset()

    if owner:

        queryset = queryset.filter(
            owner=owner,
        )

    if is_active is not None:

        queryset = queryset.filter(
            is_active=is_active,
        )

    return queryset


# =============================================================================
# Filter Orders
# =============================================================================

def filter_orders(
    *,
    restaurant,
    status=None,
    payment_status=None,
    order_type=None,
    kitchen_status=None,
    delivery_status=None,
):
    """
    Filter restaurant orders.
    """

    queryset = list_orders(
        restaurant=restaurant,
    )

    if status:

        queryset = queryset.filter(
            status=status,
        )

    if payment_status:

        queryset = queryset.filter(
            payment_status=payment_status,
        )

    if order_type:

        queryset = queryset.filter(
            order_type=order_type,
        )

    if kitchen_status:

        queryset = queryset.filter(
            kitchen_status=kitchen_status,
        )

    if delivery_status:

        queryset = queryset.filter(
            delivery_status=delivery_status,
        )

    return queryset


# =============================================================================
# Filter Staff
# =============================================================================

def filter_staff(
    *,
    restaurant,
    role=None,
    is_active=None,
    is_on_shift=None,
):
    """
    Filter staff.
    """

    queryset = list_staff(
        restaurant=restaurant,
    )

    if role:

        queryset = queryset.filter(
            role=role,
        )

    if is_active is not None:

        queryset = queryset.filter(
            is_active=is_active,
        )

    if is_on_shift is not None:

        queryset = queryset.filter(
            is_on_shift=is_on_shift,
        )

    return queryset


# =============================================================================
# Filter Food Items
# =============================================================================

def filter_food_items(
    *,
    restaurant,
    category=None,
    meal_type=None,
    is_active=None,
):
    """
    Filter menu items.
    """

    queryset = list_food_items(
        restaurant=restaurant,
    )

    if category:

        queryset = queryset.filter(
            category=category,
        )

    if meal_type:

        queryset = queryset.filter(
            meal_type=meal_type,
        )

    if is_active is not None:

        queryset = queryset.filter(
            is_active=is_active,
        )

    return queryset


# =============================================================================
# Filter Delivery Partners
# =============================================================================

def filter_delivery_partners(
    *,
    restaurant,
    is_available=None,
):
    """
    Filter delivery partners.
    """

    queryset = list_delivery_partners(
        restaurant=restaurant,
    )

    if is_available is not None:

        queryset = queryset.filter(
            is_available=is_available,
        )

    return queryset


# =============================================================================
# Recent Orders
# =============================================================================

def get_recent_orders(
    *,
    restaurant,
    limit=10,
):
    """
    Return recent restaurant orders.
    """

    return (

        list_orders(
            restaurant=restaurant,
        )[:limit]

    )


# =============================================================================
# Recent Kitchen Notes
# =============================================================================

def get_recent_kitchen_notes(
    *,
    restaurant,
    limit=10,
):
    """
    Return recent kitchen notes.
    """

    return (

        list_kitchen_notes(
            restaurant=restaurant,
        )[:limit]

    )