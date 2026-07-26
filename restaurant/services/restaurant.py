# restaurant/services/restaurant.py


# =============================================================================
# Imports
# =============================================================================

from requests import request
from rest_framework.exceptions import NotFound
import logging
import os
from typing import Optional
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
    ValidationError,
)

from restaurant.models import Restaurant, AuditLog

from django.db import transaction

from restaurant.services.audit import (
    audit_restaurant,
)

from restaurant.services.common import (
    get_restaurant,
)

from restaurant.services.hooks import (
    on_restaurant_updated,
    on_restaurant_deleted,
)

from restaurant.services.queries import (
    list_nearby_restaurants,
    get_restaurant_queryset,
    list_restaurants
)

# =============================================================================
# Query Services
# =============================================================================


from math import radians, sin, cos, sqrt, atan2

from django.db.models import Count, Sum

# =============================================================================
# Dashboard Services
# =============================================================================

from decimal import Decimal

from django.db.models import Avg, Count, Sum
from django.utils import timezone


# =============================================================================
# Logger
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_LOGO = "default/default-logo.png"

DEFAULT_COVER = "default/default-cover.jpg"


# =============================================================================
# My Restaurant
# =============================================================================

def get_my_restaurant(
    *,
    user,
):
    """
    Return the authenticated user's restaurant.

    Parameters
    ----------
    user : User
        Authenticated user requesting the restaurant.
    """

    try:
        return (
            Restaurant.objects
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
            .get(
                owner=user,
                is_deleted=False,
            )
        )

    except Restaurant.DoesNotExist:
        raise NotFound(
            "Restaurant not found.",
        )


# =============================================================================
# Restaurant Detail
# =============================================================================


def get_restaurant_detail(
    *,
    restaurant_id,
):
    """
    Return restaurant details.
    """

    return get_restaurant(
        restaurant_id=restaurant_id,
    )


# def get_restaurant_detail(
#     *,
#     restaurant_id,
# ):
#     """
#     Return a restaurant by ID.
#     """

#     try:

#         return (

#             get_restaurant_queryset()

#             .get(
#                 id=restaurant_id,
#             )

#         )

#     except Restaurant.DoesNotExist:

#         raise NotFound(
#             "Restaurant not found.",
#         )






# =============================================================================
# Update Restaurant
# =============================================================================

@transaction.atomic
def update_restaurant(
    *,
    restaurant_id,
    validated_data,
    staff=None,
    request=None,
):
    """
    Update restaurant information.
    """

    restaurant = get_restaurant(
        restaurant_id=restaurant_id,
    )

    for field, value in validated_data.items():

        setattr(
            restaurant,
            field,
            value,
        )

    restaurant.save()

    audit_restaurant(

        restaurant=restaurant,

        action=AuditLog.Action.RESTAURANT_UPDATED,

        staff=staff,

        request=request,

    )

    on_restaurant_updated(
        restaurant=restaurant,
    )

    return restaurant


# =============================================================================
# Delete Restaurant
# =============================================================================

@transaction.atomic
def delete_restaurant(
    *,
    restaurant_id,
    staff=None,
    request=None,
):
    """
    Soft delete a restaurant.
    """

    restaurant = get_restaurant(
        restaurant_id=restaurant_id,
    )

    restaurant.is_deleted = True

    restaurant.is_active = False

    restaurant.save(
        update_fields=[
            "is_deleted",
            "is_active",
        ]
    )

    audit_restaurant(

        restaurant=restaurant,

        action=AuditLog.Action.RESTAURANT_DELETED,

        staff=staff,

        request=request,

    )

    on_restaurant_deleted(
        restaurant=restaurant,
    )

    return restaurant

# =============================================================================
# Nearby Restaurants
# =============================================================================


def get_nearby_restaurants(
    *,
    latitude: float,
    longitude: float,
):
    """
    Return restaurants that can deliver to the
    specified customer location.
    """

    return list_nearby_restaurants(

        latitude=latitude,

        longitude=longitude,

    )


# =============================================================================
# Get Restaurant List
# =============================================================================


def get_restaurant_list(
    *,
    search=None,
    city=None,
    state=None,
    country=None,
    cuisine=None,
    delivery=None,
    pickup=None,
    dine_in=None,
    ordering="name",
):
    """
    Return customer-visible restaurants.

    Args:
        search (str, optional):
            Search keyword for restaurant name, cuisine, city, or description.

        city (str, optional):
            Filter by city.

        state (str, optional):
            Filter by state.

        country (str, optional):
            Filter by country.

        cuisine (str, optional):
            Filter by cuisine type.

        delivery (bool, optional):
            Filter restaurants offering delivery.

        pickup (bool, optional):
            Filter restaurants offering pickup.

        dine_in (bool, optional):
            Filter restaurants offering dine-in.

        ordering (str, optional):
            Ordering field.

    Returns:
        QuerySet:
            Filtered queryset of restaurants.
    """

    return list_restaurants(
        search=search,
        city=city,
        state=state,
        country=country,
        cuisine=cuisine,
        delivery=delivery,
        pickup=pickup,
        dine_in=dine_in,
        ordering=ordering,
    )
    


# =============================================================================
# Private Helpers
# =============================================================================

def _get_restaurant_queryset() -> QuerySet[Restaurant]:
    """
    Return the base queryset used throughout the Restaurant service layer.

    Keeping this in one place allows future filtering
    (soft delete, subscriptions, visibility, etc.)
    without changing every service function.
    """

    return (
        Restaurant.objects
        .filter(is_deleted=False)
        .select_related("owner")
        .prefetch_related(
            "categories",
            "food_items",
            "tables",
            "staff_members",
            "delivery_partners",
        )
    )
    
def _delete_file(file_field) -> None:
    """
    Safely delete an uploaded file.

    Default images are never deleted.

    Missing files are ignored.
    """

    if not file_field:
        return

    if not file_field.name:
        return

    if file_field.name in (
        DEFAULT_LOGO,
        DEFAULT_COVER,
    ):
        return

    if default_storage.exists(file_field.name):
        default_storage.delete(file_field.name)

def _replace_image(
    *,
    image_field,
    new_file,
) -> None:
    """
    Replace an existing image.

    Old uploaded image is deleted.

    Default images are preserved.
    """

    if new_file is None:
        return

    _delete_file(image_field)

    image_field.save(
        new_file.name,
        new_file,
        save=False,
    )


# =============================================================================
# Validation Helpers
# =============================================================================

def _validate_unique_owner(
    *,
    owner: User,
) -> None:
    """
    Ensure a user owns only one restaurant.
    """

    if Restaurant.objects.filter(owner=owner).exists():

        raise ValidationError(
            {
                "owner": (
                    "This user already owns a restaurant."
                )
            }
        )


def _validate_unique_name(
    *,
    name: str,
    exclude: Optional[int] = None,
) -> None:
    """
    Validate restaurant name uniqueness.

    Used by Create and Update.
    """

    queryset = Restaurant.objects.filter(
        name__iexact=name.strip(),
    )

    if exclude is not None:
        queryset = queryset.exclude(
            pk=exclude,
        )

    if queryset.exists():

        raise ValidationError(
            {
                "name": (
                    "A restaurant with this name already exists."
                )
            }
        )


def _validate_restaurant_owner(
    *,
    restaurant: Restaurant,
    user: User,
) -> None:
    """
    Ensure the authenticated user owns
    the restaurant.
    """

    if restaurant.owner_id != user.id:

        raise PermissionDenied(
            "You do not have permission "
            "to access this restaurant."
        )


# =============================================================================
# Image Helpers
# =============================================================================

def update_restaurant_logo(
    *,
    restaurant: Restaurant,
    logo,
) -> None:
    """
    Replace restaurant logo.
    """

    if logo is None:
        return

    _replace_image(
        image_field=restaurant.logo,
        new_file=logo,
    )


def update_restaurant_cover(
    *,
    restaurant: Restaurant,
    cover_image,
) -> None:
    """
    Replace restaurant cover image.
    """

    if cover_image is None:
        return

    _replace_image(
        image_field=restaurant.cover_image,
        new_file=cover_image,
    )


def delete_restaurant_logo(
    *,
    restaurant: Restaurant,
) -> None:
    """
    Delete uploaded logo.

    Falls back to the model default.
    """

    _delete_file(
        restaurant.logo,
    )

    restaurant.logo = DEFAULT_LOGO


def delete_restaurant_cover(
    *,
    restaurant: Restaurant,
) -> None:
    """
    Delete uploaded cover image.

    Falls back to the model default.
    """

    _delete_file(
        restaurant.cover_image,
    )

    restaurant.cover_image = DEFAULT_COVER
    
    
# =============================================================================
# Restaurant Services
# =============================================================================

@transaction.atomic
def create_restaurant(
    *,
    owner: User,
    validated_data: dict,
) -> Restaurant:
    """
    Create a new restaurant.

    Business Rules
    --------------
    • One restaurant per owner.
    • Restaurant names must be unique.
    • Images are handled safely.
    • Entire operation runs atomically.

    Raises
    ------
    ValidationError
        If validation fails.
    """

    _validate_unique_owner(
        owner=owner,
    )

    _validate_unique_name(
        name=validated_data["name"],
    )

    logo = validated_data.pop(
        "logo",
        None,
    )

    cover_image = validated_data.pop(
        "cover_image",
        None,
    )

    restaurant = Restaurant.objects.create(
        owner=owner,
        **validated_data,
    )

    update_restaurant_logo(
        restaurant=restaurant,
        logo=logo,
    )

    update_restaurant_cover(
        restaurant=restaurant,
        cover_image=cover_image,
    )

    restaurant.save()

    logger.info(
        "Restaurant created (id=%s owner=%s)",
        restaurant.id,
        owner.id,
    )

    return restaurant


# =============================================================================
# Restaurant Queries
# =============================================================================

def get_restaurant_by_id(
    *,
    restaurant_id: int,
) -> Restaurant:
    """
    Return a restaurant by primary key.

    Raises
    ------
    NotFound
        If the restaurant does not exist.
    """

    restaurant = (
        _get_restaurant_queryset()
        .filter(
            pk=restaurant_id,
        )
        .first()
    )

    if restaurant is None:

        raise NotFound(
            "Restaurant not found."
        )

    return restaurant


def get_restaurant_by_owner(
    *,
    owner: User,
) -> Restaurant:
    """
    Return the restaurant owned by a user.

    Raises
    ------
    NotFound
        If the owner has no restaurant.
    """

    restaurant = (
        _get_restaurant_queryset()
        .filter(
            owner=owner,
        )
        .first()
    )

    if restaurant is None:

        raise NotFound(
            "Restaurant not found."
        )

    return restaurant

# =============================================================================
# Restaurant Update
# =============================================================================

@transaction.atomic
def update_restaurant(
    *,
    restaurant: Restaurant,
    validated_data: dict,
) -> Restaurant:
    """
    Update a restaurant.

    Business Rules
    --------------
    • Restaurant must be active.
    • Restaurant name remains unique.
    • Images are safely replaced.
    • Operation is atomic.
    """

    validate_restaurant_active(
        restaurant=restaurant,
    )

    if "name" in validated_data:

        _validate_unique_name(
            name=validated_data["name"],
            exclude=restaurant.pk,
        )

    logo = validated_data.pop(
        "logo",
        None,
    )

    cover_image = validated_data.pop(
        "cover_image",
        None,
    )

    for field, value in validated_data.items():

        setattr(
            restaurant,
            field,
            value,
        )

    if logo is not None:

        update_restaurant_logo(
            restaurant=restaurant,
            logo=logo,
        )

    if cover_image is not None:

        update_restaurant_cover(
            restaurant=restaurant,
            cover_image=cover_image,
        )

    restaurant.save()

    logger.info(
        "Restaurant updated (id=%s)",
        restaurant.pk,
    )

    return restaurant


# =============================================================================
# Restaurant Delete
# =============================================================================

@transaction.atomic
def delete_restaurant(
    *,
    restaurant: Restaurant,
) -> Restaurant:
    """
    Soft delete a restaurant.
    """

    validate_restaurant_active(
        restaurant=restaurant,
    )

    restaurant.is_active = False
    restaurant.is_deleted = True
    restaurant.deleted_at = timezone.now()

    restaurant.save(
        update_fields=[
            "is_active",
            "is_deleted",
            "deleted_at",
        ]
    )

    logger.info(
        "Restaurant deleted (id=%s)",
        restaurant.pk,
    )

    return restaurant


# =============================================================================
# Restaurant Restore
# =============================================================================

@transaction.atomic
def restore_restaurant(
    *,
    restaurant: Restaurant,
) -> Restaurant:
    """
    Restore a previously deleted restaurant.
    """

    restaurant.is_active = True
    restaurant.is_deleted = False
    restaurant.deleted_at = None

    restaurant.save(
        update_fields=[
            "is_active",
            "is_deleted",
            "deleted_at",
        ]
    )

    logger.info(
        "Restaurant restored (id=%s)",
        restaurant.pk,
    )

    return restaurant


# =============================================================================
# Restaurant Exists
# =============================================================================

def restaurant_exists(
    *,
    restaurant_id: int,
) -> bool:
    """
    Return whether an active restaurant exists.
    """

    return _get_restaurant_queryset().filter(
        pk=restaurant_id,
    ).exists()


# =============================================================================
# Restaurant Name Exists
# =============================================================================

def restaurant_name_exists(
    *,
    name: str,
    exclude: int | None = None,
) -> bool:
    """
    Return whether a restaurant name already exists.
    """

    queryset = _get_restaurant_queryset().filter(
        name__iexact=name.strip(),
    )

    if exclude is not None:

        queryset = queryset.exclude(
            pk=exclude,
        )

    return queryset.exists()


# =============================================================================
# Restaurant Owner Validation
# =============================================================================

def validate_restaurant_owner(
    *,
    restaurant: Restaurant,
    user: User,
) -> None:
    """
    Ensure the authenticated user owns the restaurant.
    """

    if restaurant.owner_id != user.id:

        raise PermissionDenied(
            "You do not have permission to manage this restaurant."
        )


# =============================================================================
# Restaurant Active Validation
# =============================================================================

def validate_restaurant_active(
    *,
    restaurant: Restaurant,
) -> None:
    """
    Ensure the restaurant is active.
    """

    if restaurant.is_deleted:

        raise ValidationError(
            {
                "restaurant": (
                    "This restaurant has been deleted."
                )
            }
        )

    if not restaurant.is_active:

        raise ValidationError(
            {
                "restaurant": (
                    "This restaurant is currently inactive."
                )
            }
        )
        
        
# =============================================================================
# List Restaurants
# =============================================================================

def list_restaurants() -> QuerySet[Restaurant]:
    """
    Return all active restaurants.

    Returns
    -------
    QuerySet[Restaurant]
    """

    return (
        _get_restaurant_queryset()
        .filter(
            is_active=True,
        )
        .order_by("name")
    )


# =============================================================================
# Nearby Restaurants
# =============================================================================

def list_nearby_restaurants(
    *,
    latitude: float,
    longitude: float,
    radius_km: float = 10,
) -> list[Restaurant]:
    """
    Return restaurants within the specified radius.

    Distance is calculated using the Haversine formula.
    """

    restaurants = []

    for restaurant in list_restaurants():

        if (
            restaurant.delivery_latitude is None
            or restaurant.delivery_longitude is None
        ):
            continue

        distance = _calculate_distance(
            latitude,
            longitude,
            float(restaurant.delivery_latitude),
            float(restaurant.delivery_longitude),
        )

        if distance <= radius_km:

            restaurant.distance_km = round(
                distance,
                2,
            )

            restaurants.append(
                restaurant,
            )

    restaurants.sort(
        key=lambda restaurant: restaurant.distance_km,
    )

    return restaurants


# =============================================================================
# Restaurant Statistics
# =============================================================================

def get_restaurant_statistics(
    *,
    restaurant: Restaurant,
) -> dict:
    """
    Return restaurant statistics used by
    dashboards and reports.
    """

    validate_restaurant_active(
        restaurant=restaurant,
    )

    return {

        "categories": restaurant.categories.count(),

        "food_items": restaurant.food_items.count(),

        "tables": restaurant.tables.count(),

        "staff": restaurant.staff_members.filter(
            is_deleted=False,
        ).count(),

        "delivery_partners": restaurant.delivery_partners.filter(
            is_active=True,
        ).count(),

        "orders": restaurant.orders.filter(
            is_deleted=False,
        ).count(),

        "completed_orders": restaurant.orders.filter(
            is_completed=True,
            is_deleted=False,
        ).count(),

    }


# =============================================================================
# Distance Helper
# =============================================================================

def _calculate_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate great-circle distance
    using the Haversine formula.
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
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(d_lon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a),
    )

    return earth_radius * c


# =============================================================================
# Dashboard Summary
# =============================================================================

def get_dashboard_summary(
    *,
    restaurant: Restaurant,
) -> dict:
    """
    Return top KPI cards displayed
    on the Restaurant Dashboard.
    """

    validate_restaurant_active(
        restaurant=restaurant,
    )

    today = timezone.localdate()

    orders = restaurant.orders.filter(
        is_deleted=False,
    )

    today_orders = orders.filter(
        created_at__date=today,
    )

    return {

        "today_orders": today_orders.count(),

        "pending_orders": orders.filter(
            status="pending",
        ).count(),

        "preparing_orders": orders.filter(
            kitchen_status="preparing",
        ).count(),

        "completed_orders": orders.filter(
            is_completed=True,
        ).count(),

        "today_sales": (

            today_orders.filter(
                is_completed=True,
            ).aggregate(
                total=Sum("grand_total"),
            )["total"]

            or Decimal("0.00")

        ),

        "total_tables": restaurant.tables.count(),

        "total_staff": restaurant.staff_members.filter(
            is_deleted=False,
        ).count(),

    }


# =============================================================================
# Kitchen Statistics
# =============================================================================

def get_kitchen_statistics(
    *,
    restaurant: Restaurant,
) -> dict:
    """
    Kitchen/KDS statistics.
    """

    validate_restaurant_active(
        restaurant=restaurant,
    )

    orders = restaurant.orders.filter(
        is_deleted=False,
    )

    return {

        "new_orders": orders.filter(
            kitchen_status="new",
        ).count(),

        "preparing_orders": orders.filter(
            kitchen_status="preparing",
        ).count(),

        "ready_orders": orders.filter(
            kitchen_status="ready",
        ).count(),

        "served_orders": orders.filter(
            kitchen_status="served",
        ).count(),

        "average_preparation_time":

            restaurant.average_preparation_time,

        "kitchen_notes": restaurant.kitchen_notes.filter(
            is_deleted=False,
        ).count(),

    }


# =============================================================================
# Delivery Statistics
# =============================================================================

def get_delivery_statistics(
    *,
    restaurant: Restaurant,
) -> dict:
    """
    Delivery dashboard statistics.
    """

    validate_restaurant_active(
        restaurant=restaurant,
    )

    deliveries = restaurant.delivery_partners.filter(
        is_active=True,
    )

    delivery_orders = restaurant.orders.filter(
        order_type="delivery",
        is_deleted=False,
    )

    return {

        "delivery_enabled": restaurant.delivery_enabled,

        "active_delivery_partners": deliveries.count(),

        "delivery_orders": delivery_orders.count(),

        "pending_delivery_orders": delivery_orders.filter(
            delivery_status="pending",
        ).count(),

        "out_for_delivery": delivery_orders.filter(
            delivery_status="out_for_delivery",
        ).count(),

        "delivered_orders": delivery_orders.filter(
            delivery_status="delivered",
        ).count(),

        "free_delivery_radius":

            restaurant.free_delivery_radius_km,

        "maximum_delivery_radius":

            restaurant.maximum_delivery_radius_km,

    }


# =============================================================================
# Sales Statistics
# =============================================================================

def get_sales_statistics(
    *,
    restaurant: Restaurant,
) -> dict:
    """
    Revenue analytics.
    """

    validate_restaurant_active(
        restaurant=restaurant,
    )

    completed_orders = restaurant.orders.filter(
        is_completed=True,
        is_deleted=False,
    )

    sales = completed_orders.aggregate(

        total_sales=Sum("grand_total"),

        average_order=Avg("grand_total"),

        total_orders=Count("id"),

    )

    return {

        "total_sales":

            sales["total_sales"]

            or Decimal("0.00"),

        "average_order_value":

            sales["average_order"]

            or Decimal("0.00"),

        "completed_orders":

            sales["total_orders"],

        "tax_percentage":

            restaurant.tax_percentage,

        "currency":

            restaurant.currency_code,

        "currency_symbol":

            restaurant.currency_symbol,

    }


# =============================================================================
# Staff Statistics
# =============================================================================

def get_staff_statistics(
    *,
    restaurant: Restaurant,
) -> dict:
    """
    Staff dashboard statistics.
    """

    validate_restaurant_active(
        restaurant=restaurant,
    )

    staff = restaurant.staff_members.filter(
        is_deleted=False,
    )

    attendance = restaurant.staff_attendances.filter(
        is_deleted=False,
    )

    return {

        "total_staff":

            staff.count(),

        "active_staff":

            staff.filter(
                is_active=True,
            ).count(),

        "inactive_staff":

            staff.filter(
                is_active=False,
            ).count(),

        "today_attendance":

            attendance.filter(
                date=timezone.localdate(),
            ).count(),

        "working_staff":

            attendance.filter(
                date=timezone.localdate(),
                check_out_time__isnull=True,
            ).count(),

        "staff_on_break":

            restaurant.staff_breaks.filter(
                end_time__isnull=True,
            ).count(),

    }
    
    
    
