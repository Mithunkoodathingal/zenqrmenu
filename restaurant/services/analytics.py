# restaurants/services/analytics.py

"""
Analytics Services

Provides reporting and business metrics for the Restaurant module.

Rules
-----
• Read-only
• No side effects
• No model updates
• No validation
"""

from datetime import timedelta

from django.db.models import (
    Avg,
    Count,
    Sum,
)
from django.utils import timezone

from restaurant.models import (
    FoodItem,
    Order,
    OrderItem,
    Staff,
    DeliveryPartner,
)




# =============================================================================
# Placeholder For - Get_Dashboard_Cards - and - Get_Sales_Chart -
# =============================================================================

def get_dashboard_cards(restaurant):
    return {
        "today_sales": 0,
        "today_orders": 0,
        "pending_orders": 0,
        "active_tables": 0,
    }


def get_sales_chart(restaurant):
    return []

# =============================================================================
# Restaurant Statistics
# =============================================================================

def get_restaurant_statistics(
    *,
    restaurant,
):
    """
    General restaurant statistics.
    """

    orders = Order.objects.filter(
        restaurant=restaurant,
        is_deleted=False,
    )

    return {

        "orders": orders.count(),

        "completed_orders": orders.filter(
            is_completed=True,
        ).count(),

        "categories": restaurant.categories.count(),

        "food_items": restaurant.food_items.count(),

        "tables": restaurant.tables.count(),

        "staff": restaurant.staff_members.filter(
            is_deleted=False,
        ).count(),

        "delivery_partners": restaurant.delivery_partners.filter(
            is_active=True,
        ).count(),

    }


# =============================================================================
# Sales Statistics
# =============================================================================

def get_sales_statistics(
    *,
    restaurant,
):
    """
    Revenue analytics.
    """

    queryset = Order.objects.filter(

        restaurant=restaurant,

        payment_status="paid",

        is_deleted=False,

    )

    sales = queryset.aggregate(

        total_sales=Sum("grand_total"),

        average_order=Avg("grand_total"),

        total_orders=Count("id"),

    )

    return {

        "total_sales":

            sales["total_sales"] or 0,

        "average_order":

            sales["average_order"] or 0,

        "paid_orders":

            sales["total_orders"],

    }


# =============================================================================
# Daily Sales
# =============================================================================

def get_daily_sales(
    *,
    restaurant,
):
    """
    Today's sales.
    """

    today = timezone.localdate()

    return (

        Order.objects

        .filter(

            restaurant=restaurant,

            payment_status="paid",

            created_at__date=today,

            is_deleted=False,

        )

        .aggregate(

            total=Sum("grand_total"),

        )["total"]

        or 0

    )


# =============================================================================
# Weekly Sales
# =============================================================================

def get_weekly_sales(
    *,
    restaurant,
):
    """
    Last 7 days sales.
    """

    start = timezone.localdate() - timedelta(days=6)

    return (

        Order.objects

        .filter(

            restaurant=restaurant,

            payment_status="paid",

            created_at__date__gte=start,

            is_deleted=False,

        )

        .aggregate(

            total=Sum("grand_total"),

        )["total"]

        or 0

    )


# =============================================================================
# Monthly Sales
# =============================================================================

def get_monthly_sales(
    *,
    restaurant,
):
    """
    Current month sales.
    """

    today = timezone.localdate()

    start = today.replace(day=1)

    return (

        Order.objects

        .filter(

            restaurant=restaurant,

            payment_status="paid",

            created_at__date__gte=start,

            is_deleted=False,

        )

        .aggregate(

            total=Sum("grand_total"),

        )["total"]

        or 0

    )


# =============================================================================
# Yearly Sales
# =============================================================================

def get_yearly_sales(
    *,
    restaurant,
):
    """
    Current year sales.
    """

    today = timezone.localdate()

    return (

        Order.objects

        .filter(

            restaurant=restaurant,

            payment_status="paid",

            created_at__year=today.year,

            is_deleted=False,

        )

        .aggregate(

            total=Sum("grand_total"),

        )["total"]

        or 0

    )


# =============================================================================
# Order Statistics
# =============================================================================

def get_order_statistics(
    *,
    restaurant,
):
    """
    Order analytics.
    """

    queryset = Order.objects.filter(

        restaurant=restaurant,

        is_deleted=False,

    )

    return {

        "total_orders": queryset.count(),

        "pending": queryset.filter(
            status="pending",
        ).count(),

        "confirmed": queryset.filter(
            status="confirmed",
        ).count(),

        "preparing": queryset.filter(
            status="preparing",
        ).count(),

        "ready": queryset.filter(
            status="ready",
        ).count(),

        "completed": queryset.filter(
            status="completed",
        ).count(),

        "cancelled": queryset.filter(
            status="cancelled",
        ).count(),

    }


# =============================================================================
# Menu Statistics
# =============================================================================

def get_menu_statistics(
    *,
    restaurant,
):
    """
    Menu analytics.
    """

    return {

        "categories": restaurant.categories.count(),

        "food_items": restaurant.food_items.count(),

        "available_items":

            restaurant.food_items.filter(

                is_active=True,

                is_paused=False,

            ).count(),

        "paused_items":

            restaurant.food_items.filter(

                is_paused=True,

            ).count(),

    }


# =============================================================================
# Staff Statistics
# =============================================================================

def get_staff_statistics(
    *,
    restaurant,
):
    """
    Staff analytics.
    """

    queryset = Staff.objects.filter(

        restaurant=restaurant,

        is_deleted=False,

    )

    return {

        "total_staff": queryset.count(),

        "active_staff":

            queryset.filter(
                is_active=True,
            ).count(),

        "on_shift":

            queryset.filter(
                is_on_shift=True,
            ).count(),

        "on_break":

            queryset.filter(
                is_on_break=True,
            ).count(),

    }


# =============================================================================
# Delivery Statistics
# =============================================================================

def get_delivery_statistics(
    *,
    restaurant,
):
    """
    Delivery analytics.
    """

    partners = DeliveryPartner.objects.filter(
        restaurant=restaurant,
    )

    orders = Order.objects.filter(
        restaurant=restaurant,
        order_type="delivery",
        is_deleted=False,
    )

    return {

        "delivery_enabled":

            restaurant.delivery_enabled,

        "partners":

            partners.count(),

        "available_partners":

            partners.filter(
                is_available=True,
            ).count(),

        "delivery_orders":

            orders.count(),

        "delivered":

            orders.filter(
                delivery_status="delivered",
            ).count(),

    }


# =============================================================================
# Top Selling Items
# =============================================================================

def get_top_selling_items(
    *,
    restaurant,
    limit=10,
):
    """
    Return best-selling menu items.
    """

    return (

        OrderItem.objects

        .filter(

            order__restaurant=restaurant,

            order__payment_status="paid",

            order__is_deleted=False,

        )

        .values(

            "food_item",

            "food_item__name",

        )

        .annotate(

            quantity_sold=Sum("quantity"),

        )

        .order_by(

            "-quantity_sold",

        )[:limit]

    )


# =============================================================================
# Customer Statistics
# =============================================================================

def get_customer_statistics(
    *,
    restaurant,
):
    """
    Customer analytics.
    """

    queryset = Order.objects.filter(

        restaurant=restaurant,

        is_deleted=False,

    )

    return {

        "unique_customers":

            queryset.values(
                "customer_phone",
            ).distinct().count(),

        "repeat_orders":

            queryset.values(
                "customer_phone",
            ).annotate(
                total=Count("id"),
            ).filter(
                total__gt=1,
            ).count(),

    }
    
    
