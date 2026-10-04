from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone

# from io import BytesIO
# import csv
# from openpyxl import Workbook
# from weasyprint import HTML
# from django.http import HttpResponse

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from restaurant.models import (
    Restaurant,
    FoodItem,
    Category,
    Table,
    Order,
    Staff,
    DeliveryPartner,
)

from restaurant.feature_models import (
    Coupon,
    CouponRedemption,
    Review,
    InventoryItem,
    InventoryTransaction,
    InventoryPurchase,
    Branch,
    AppNotification,
    NotificationPreference,
    ScheduledReport,
)

from restaurant.services.common import get_restaurant
from restaurant.services.delivery import (
    calculate_distance,
    get_delivery_summary,
)
from restaurant.services.dashboard import get_dashboard_data


# =============================================================================
# COMMON HELPERS
# =============================================================================

def restaurant_or_404(request):
    restaurant = get_restaurant(request)

    if restaurant is None:
        return None, Response(
            {
                "success": False,
                "message": "Restaurant not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    return restaurant, None


def decimal_value(value):
    if value is None:
        return 0
    return float(value)


def notification_payload(notification):
    return {
        "id": notification.id,
        "type": notification.notification_type,
        "title": notification.title,
        "message": notification.message,
        "order_id": notification.order_id,
        "read": notification.read,
        "created_at": notification.created_at,
    }


# =============================================================================
# SEARCH
# =============================================================================

class SearchAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = str(request.query_params.get("q", "")).strip()
        entities = request.query_params.get("entities")

        if not q:
            return Response([])

        requested = None

        if entities:
            requested = {
                value.strip()
                for value in entities.split(",")
                if value.strip()
            }

        restaurant, error = restaurant_or_404(request)

        if error:
            return error

        results = []

        def enabled(entity):
            return requested is None or entity in requested

        if enabled("order"):
            orders = Order.objects.filter(
                restaurant=restaurant,
                is_deleted=False,
            ).filter(
                order_number__icontains=q
            )[:10]

            for order in orders:
                results.append(
                    {
                        "entity": "order",
                        "id": order.id,
                        "title": order.order_number,
                        "subtitle": order.status,
                    }
                )

        if enabled("menu_item"):
            items = FoodItem.objects.filter(
                restaurant=restaurant,
                name__icontains=q,
            )[:10]

            for item in items:
                results.append(
                    {
                        "entity": "menu_item",
                        "id": item.id,
                        "title": item.name,
                        "subtitle": str(item.price),
                    }
                )

        if enabled("table"):
            tables = Table.objects.filter(
                restaurant=restaurant,
                table_number__icontains=q,
            )[:10]

            for table in tables:
                results.append(
                    {
                        "entity": "table",
                        "id": table.id,
                        "title": f"Table {table.table_number}",
                    }
                )

        if enabled("customer"):
            orders = (
                Order.objects
                .filter(
                    restaurant=restaurant,
                    is_deleted=False,
                )
                .filter(
                    customer_name__icontains=q
                )
                .order_by("-created_at")[:10]
            )

            seen = set()

            for order in orders:
                key = order.customer_phone or order.customer_name

                if key in seen:
                    continue

                seen.add(key)

                results.append(
                    {
                        "entity": "customer",
                        "id": order.id,
                        "title": order.customer_name,
                        "subtitle": order.customer_phone,
                    }
                )

        if enabled("delivery_partner"):
            partners = DeliveryPartner.objects.filter(
                restaurant=restaurant,
            ).filter(
                first_name__icontains=q
            )[:10]

            for partner in partners:
                results.append(
                    {
                        "entity": "delivery_partner",
                        "id": partner.id,
                        "title": partner.full_name,
                        "subtitle": partner.phone,
                    }
                )

        if enabled("staff"):
            staff = Staff.objects.filter(
                restaurant=restaurant,
                is_deleted=False,
            ).filter(
                first_name__icontains=q
            )[:10]

            for member in staff:
                results.append(
                    {
                        "entity": "staff",
                        "id": member.id,
                        "title": f"{member.first_name} {member.last_name}".strip(),
                        "subtitle": member.role,
                    }
                )

        return Response(results[:50])


# =============================================================================
# DELIVERY LOCATION
# =============================================================================

class DeliveryLocationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant, error = restaurant_or_404(request)

        if error:
            return error

        return Response(
            {
                "latitude": restaurant.delivery_latitude,
                "longitude": restaurant.delivery_longitude,
                "address": restaurant.address,
                "city": restaurant.city,
                "state": restaurant.state,
                "country": restaurant.country,
                "pincode": restaurant.pincode,
                "phone_country_code": restaurant.phone_country_code,
            }
        )

    def put(self, request):
        restaurant, error = restaurant_or_404(request)

        if error:
            return error

        fields = {
            "latitude": "delivery_latitude",
            "longitude": "delivery_longitude",
            "address": "address",
            "city": "city",
            "state": "state",
            "country": "country",
            "pincode": "pincode",
        }

        changed = []

        for incoming, model_field in fields.items():
            if incoming in request.data:
                setattr(
                    restaurant,
                    model_field,
                    request.data[incoming],
                )
                changed.append(model_field)

        if not changed:
            return Response(
                {
                    "message": "No supported location fields supplied."
                },
                status=400,
            )

        restaurant.save(update_fields=changed)

        return self.get(request)


# =============================================================================
# DELIVERY ZONE
# =============================================================================

class DeliveryZoneAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant, error = restaurant_or_404(request)

        if error:
            return error

        return Response(
            {
                "enable_delivery": restaurant.delivery_enabled,
                "enable_pickup": restaurant.pickup_enabled,
                "enable_dinein_payment": True,
                "max_delivery_km": decimal_value(
                    restaurant.maximum_delivery_radius_km
                ),
                "free_delivery_km": decimal_value(
                    restaurant.free_delivery_radius_km
                ),
                "charge_per_extra_km": decimal_value(
                    restaurant.delivery_charge_per_km
                ),
                "minimum_delivery_order": decimal_value(
                    restaurant.minimum_delivery_order
                ),
                "average_prep_minutes": restaurant.average_preparation_time,
            }
        )

    def put(self, request):
        restaurant, error = restaurant_or_404(request)

        if error:
            return error

        mapping = {
            "enable_delivery": "delivery_enabled",
            "enable_pickup": "pickup_enabled",
            "max_delivery_km": "maximum_delivery_radius_km",
            "free_delivery_km": "free_delivery_radius_km",
            "charge_per_extra_km": "delivery_charge_per_km",
            "minimum_delivery_order": "minimum_delivery_order",
            "average_prep_minutes": "average_preparation_time",
        }

        changed = []

        for incoming, model_field in mapping.items():
            if incoming in request.data:
                setattr(
                    restaurant,
                    model_field,
                    request.data[incoming],
                )
                changed.append(model_field)

        if changed:
            restaurant.save(update_fields=changed)

        return self.get(request)


# =============================================================================
# DELIVERY QUOTE
# =============================================================================

class DeliveryQuoteAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        restaurant_id = request.data.get("restaurant_id")

        restaurant = get_object_or_404(
            Restaurant,
            id=restaurant_id,
            is_active=True,
            is_deleted=False,
        )

        try:
            latitude = float(request.data["latitude"])
            longitude = float(request.data["longitude"])
        except (KeyError, TypeError, ValueError):
            return Response(
                {
                    "message": "Valid latitude and longitude are required."
                },
                status=400,
            )

        summary = get_delivery_summary(
            restaurant,
            latitude,
            longitude,
        )

        distance = summary.get("distance_km", 0)

        inside = (
            distance <=
            float(restaurant.maximum_delivery_radius_km)
        )

        charge = 0

        if inside:
            if distance > float(restaurant.free_delivery_radius_km):
                extra_km = (
                    distance -
                    float(restaurant.free_delivery_radius_km)
                )
                charge = (
                    extra_km *
                    float(restaurant.delivery_charge_per_km)
                )

        return Response(
            {
                "distance_km": distance,
                "inside_area": inside,
                "delivery_charge": round(charge, 2),
                "free_delivery_remaining_km": max(
                    float(restaurant.free_delivery_radius_km) -
                    distance,
                    0,
                ),
                "estimated_prep_minutes":
                    restaurant.average_preparation_time,
                "estimated_delivery_minutes":
                    restaurant.average_preparation_time + 30,
                "minimum_order_amount":
                    decimal_value(
                        restaurant.minimum_delivery_order
                    ),
                "currency_code": restaurant.currency_code,
                "currency_symbol": restaurant.currency_symbol,
            }
        )


# =============================================================================
# NEARBY RESTAURANTS
# =============================================================================

class NearbyRestaurantsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            latitude = float(request.query_params["latitude"])
            longitude = float(request.query_params["longitude"])
        except (KeyError, TypeError, ValueError):
            return Response(
                {
                    "message": "latitude and longitude are required."
                },
                status=400,
            )

        restaurants = Restaurant.objects.filter(
            is_active=True,
            is_deleted=False,
            delivery_enabled=True,
            delivery_latitude__isnull=False,
            delivery_longitude__isnull=False,
        )

        results = []

        for restaurant in restaurants:
            distance = calculate_distance(
                latitude,
                longitude,
                float(restaurant.delivery_latitude),
                float(restaurant.delivery_longitude),
            )

            if distance > float(
                restaurant.maximum_delivery_radius_km
            ):
                continue

            results.append(
                {
                    "id": restaurant.id,
                    "name": restaurant.name,
                    "logo": (
                        restaurant.logo.url
                        if restaurant.logo
                        else None
                    ),
                    "cover_image": (
                        restaurant.cover_image.url
                        if restaurant.cover_image
                        else None
                    ),
                    "distance_km": round(distance, 2),
                    "inside_delivery_area": True,
                    "free_delivery_km":
                        decimal_value(
                            restaurant.free_delivery_radius_km
                        ),
                    "charge_per_extra_km":
                        decimal_value(
                            restaurant.delivery_charge_per_km
                        ),
                    "minimum_delivery_order":
                        decimal_value(
                            restaurant.minimum_delivery_order
                        ),
                    "pickup_available":
                        restaurant.pickup_enabled,
                    "delivery_available":
                        restaurant.delivery_enabled,
                    "average_prep_minutes":
                        restaurant.average_preparation_time,
                    "currency_symbol":
                        restaurant.currency_symbol,
                }
            )

        results.sort(
            key=lambda value: value["distance_km"]
        )

        return Response(results)


# =============================================================================
# DASHBOARD WIDGETS
# =============================================================================

class DashboardWidgetsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant, error = restaurant_or_404(request)

        if error:
            return error

        dashboard = get_dashboard_data(restaurant)

        cards = dashboard.get("cards", {})
        sales = dashboard.get("sales", {})
        orders = dashboard.get("orders", {})
        delivery = dashboard.get("delivery", {})

        return Response(
            {
                "todays_orders": cards.get(
                    "today_orders",
                    0,
                ),
                "live_orders": (
                    orders.get("pending", 0) +
                    orders.get("confirmed", 0) +
                    orders.get("preparing", 0) +
                    orders.get("ready", 0)
                ),
                "kitchen_load": orders.get(
                    "preparing",
                    0,
                ),
                "delivery_load": delivery.get(
                    "delivery_orders",
                    0,
                ),
                "pending_payments": Order.objects.filter(
                    restaurant=restaurant,
                    payment_status__in=[
                        "pending",
                        "created",
                    ],
                    is_deleted=False,
                ).count(),
                "todays_revenue": decimal_value(
                    sales.get("today_sales", 0)
                ),
                "avg_prep_minutes":
                    restaurant.average_preparation_time,
            }
        )


# =============================================================================
# ANALYTICS
# =============================================================================

class AnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, metric):
        restaurant, error = restaurant_or_404(request)

        if error:
            return error

        orders = Order.objects.filter(
            restaurant=restaurant,
            is_deleted=False,
        )

        paid_orders = orders.filter(
            payment_status="paid"
        )

        total_revenue = decimal_value(
            paid_orders.aggregate(
                total=Sum("grand_total")
            )["total"]
        )

        total_orders = orders.count()

        if metric in {"summary", "executive"}:
            return Response(
                {
                    "currency": restaurant.currency_code,
                    "kpis": [
                        {
                            "key": "revenue",
                            "label": "Revenue",
                            "value": total_revenue,
                            "format": "currency",
                        },
                        {
                            "key": "orders",
                            "label": "Orders",
                            "value": total_orders,
                            "format": "number",
                        },
                        {
                            "key": "average_order",
                            "label": "Average Order",
                            "value": (
                                total_revenue / total_orders
                                if total_orders
                                else 0
                            ),
                            "format": "currency",
                        },
                    ],
                    "generated_at": timezone.now(),
                }
            )

        if metric in {
            "sales",
            "daily-sales",
            "monthly-sales",
        }:
            points = []

            grouped = (
                paid_orders
                .values("created_at__date")
                .annotate(
                    total=Sum("grand_total")
                )
                .order_by("created_at__date")
            )

            for row in grouped:
                points.append(
                    {
                        "label": str(
                            row["created_at__date"]
                        ),
                        "value": decimal_value(
                            row["total"]
                        ),
                    }
                )

            return Response(
                {
                    "granularity": "day",
                    "points": points,
                    "total": total_revenue,
                    "currency":
                        restaurant.currency_code,
                }
            )

        if metric == "menu":
            items = (
                paid_orders
                .values(
                    "order_items__food_item",
                    "order_items__food_item__name",
                )
                .annotate(
                    quantity=Sum(
                        "order_items__quantity"
                    ),
                    revenue=Sum(
                        "order_items__line_total"
                    ),
                )
                .order_by("-quantity")[:20]
            )

            ranked = []

            for item in items:
                ranked.append(
                    {
                        "id":
                            item[
                                "order_items__food_item"
                            ],
                        "name":
                            item[
                                "order_items__food_item__name"
                            ],
                        "quantity":
                            item["quantity"] or 0,
                        "revenue":
                            decimal_value(
                                item["revenue"]
                            ),
                        "share_percent": 0,
                    }
                )

            return Response(
                {
                    "top_categories": [],
                    "top_items": ranked,
                    "top_addons": [],
                    "bottom_items": [],
                    "currency":
                        restaurant.currency_code,
                }
            )

        if metric == "customers":
            customers = (
                orders
                .values("customer_phone")
                .annotate(
                    orders=Count("id"),
                    spend=Sum("grand_total"),
                )
                .order_by("-spend")
            )

            unique = customers.count()

            repeat = customers.filter(
                orders__gt=1
            ).count()

            return Response(
                {
                    "new_customers":
                        max(unique - repeat, 0),
                    "returning_customers":
                        repeat,
                    "repeat_purchase_percent":
                        (
                            repeat / unique * 100
                            if unique
                            else 0
                        ),
                    "average_spend":
                        (
                            total_revenue / unique
                            if unique
                            else 0
                        ),
                    "top_customers": [],
                    "favorite_categories": [],
                    "currency":
                        restaurant.currency_code,
                }
            )

        if metric == "delivery":
            delivery_orders = orders.filter(
                order_type="delivery"
            )

            delivered = delivery_orders.filter(
                delivery_status="delivered"
            ).count()

            return Response(
                {
                    "average_delivery_time_minutes": 0,
                    "average_distance_km": 0,
                    "success_rate_percent": (
                        delivered /
                        delivery_orders.count() *
                        100
                        if delivery_orders.count()
                        else 0
                    ),
                    "late_delivery_percent": 0,
                    "delivery_revenue": decimal_value(
                        delivery_orders.filter(
                            payment_status="paid"
                        ).aggregate(
                            total=Sum("grand_total")
                        )["total"]
                    ),
                    "partner_performance": [],
                }
            )

        if metric == "staff":
            members = Staff.objects.filter(
                restaurant=restaurant,
                is_deleted=False,
            )

            return Response(
                {
                    "members": [
                        {
                            "id": member.id,
                            "name":
                                f"{member.first_name} "
                                f"{member.last_name}".strip(),
                            "role": member.role,
                            "orders_handled": 0,
                            "kitchen_workload": 0,
                            "delivery_workload": 0,
                            "shift_utilization_percent": 0,
                        }
                        for member in members
                    ]
                }
            )

        if metric == "coupons":
            redemptions = CouponRedemption.objects.filter(
                coupon__restaurant=restaurant
            )

            discount = decimal_value(
                redemptions.aggregate(
                    total=Sum("discount_amount")
                )["total"]
            )

            return Response(
                {
                    "total_redemptions":
                        redemptions.count(),
                    "redemption_rate_percent": 0,
                    "revenue_generated": 0,
                    "discount_given": discount,
                    "top_coupons": [],
                    "currency":
                        restaurant.currency_code,
                }
            )

        if metric == "refunds":
            return Response(
                {
                    "total_refunded": 0,
                    "full_refunds": 0,
                    "partial_refunds": 0,
                    "failed_refunds": 0,
                    "by_reason": [],
                    "by_gateway": [],
                    "by_time": [],
                    "currency":
                        restaurant.currency_code,
                }
            )

        if metric == "kitchen":
            return Response(
                {
                    "average_prep_time_minutes":
                        restaurant.average_preparation_time,
                    "queue_length":
                        orders.filter(
                            status__in=[
                                "pending",
                                "confirmed",
                                "preparing",
                            ]
                        ).count(),
                    "utilization_percent": 0,
                    "slowest_orders": [],
                    "fastest_orders": [],
                }
            )

        if metric in {
            "heatmap",
            "payment-methods",
            "revenue",
            "top-customers",
            "top-items",
        }:
            return Response([])

        return Response(
            {
                "message":
                    f"Unknown analytics metric: {metric}"
            },
            status=404,
        )


# =============================================================================
# RESTAURANT SETTINGS
# =============================================================================

class RestaurantWorkingHoursAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant, error = restaurant_or_404(request)

        if error:
            return error

        return Response(
            restaurant.working_hours or {}
        )

    def put(self, request):
        restaurant, error = restaurant_or_404(request)

        if error:
            return error

        if not isinstance(request.data, dict):
            return Response(
                {
                    "message":
                        "Working hours must be an object."
                },
                status=400,
            )

        restaurant.working_hours = request.data
        restaurant.save(
            update_fields=["working_hours"]
        )

        return Response(
            restaurant.working_hours
        )


class RestaurantSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant, error = restaurant_or_404(request)

        if error:
            return error

        return Response(
            {
                "name": restaurant.name,
                "address": restaurant.address,
                "about": restaurant.about,
                "cuisine_type": restaurant.cuisine_type,
                "phone": restaurant.phone,
                "email": restaurant.email,
                "website": restaurant.website,
                "tax_enabled": restaurant.tax_enabled,
                "tax_name": restaurant.tax_name,
                "tax_percentage":
                    decimal_value(
                        restaurant.tax_percentage
                    ),
                "prices_include_tax":
                    restaurant.prices_include_tax,
                "currency_code":
                    restaurant.currency_code,
                "currency_symbol":
                    restaurant.currency_symbol,
                "invoice_prefix":
                    restaurant.invoice_prefix,
                "footer_message":
                    restaurant.footer_message,
                "timezone":
                    restaurant.timezone,
            }
        )

    def put(self, request):
        restaurant, error = restaurant_or_404(request)

        if error:
            return error

        allowed = [
            "name",
            "address",
            "about",
            "cuisine_type",
            "phone",
            "email",
            "website",
            "tax_enabled",
            "tax_name",
            "tax_percentage",
            "prices_include_tax",
            "currency_code",
            "currency_symbol",
            "invoice_prefix",
            "footer_message",
            "timezone",
        ]

        changed = []

        for field in allowed:
            if field in request.data:
                setattr(
                    restaurant,
                    field,
                    request.data[field],
                )
                changed.append(field)

        if changed:
            restaurant.save(update_fields=changed)

        return self.get(request)
    
    
# =============================================================================
# INVENTORY
# =============================================================================

class InventoryIngredientsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant, error = restaurant_or_404(request)

        if error:
            return error

        items = InventoryItem.objects.filter(
            restaurant=restaurant,
            is_active=True,
        )

        return Response(
            [
                {
                    "id": item.id,
                    "name": item.name,
                    "unit": item.unit,
                    "stock": decimal_value(item.quantity),
                    "low_stock_threshold":
                        decimal_value(item.reorder_level),
                    "status": (
                        "out_of_stock"
                        if item.quantity <= 0
                        else "low_stock"
                        if item.quantity <= item.reorder_level
                        else "in_stock"
                    ),
                    "linked_menu_item_ids": (
                        [item.food_item_id]
                        if item.food_item_id
                        else []
                    ),
                    "updated_at": item.updated_at,
                }
                for item in items
            ]
        )

    def post(self, request):
        restaurant, error = restaurant_or_404(request)

        if error:
            return error

        item = InventoryItem.objects.create(
            restaurant=restaurant,
            name=request.data["name"],
            unit=request.data.get("unit", "unit"),
            quantity=request.data.get("stock", 0),
            reorder_level=request.data.get(
                "low_stock_threshold",
                0,
            ),
            food_item_id=request.data.get(
                "food_item_id"
            ),
        )

        return Response(
            {
                "id": item.id,
                "name": item.name,
                "unit": item.unit,
                "stock": decimal_value(item.quantity),
                "low_stock_threshold":
                    decimal_value(item.reorder_level),
            },
            status=201,
        )


class InventoryIngredientDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, ingredient_id):
        restaurant, error = restaurant_or_404(request)

        if error:
            return None, error

        return (
            get_object_or_404(
                InventoryItem,
                id=ingredient_id,
                restaurant=restaurant,
            ),
            None,
        )

    def patch(self, request, ingredient_id):
        item, error = self.get_object(
            request,
            ingredient_id,
        )

        if error:
            return error

        fields = {
            "name": "name",
            "unit": "unit",
            "stock": "quantity",
            "low_stock_threshold": "reorder_level",
        }

        changed = []

        for incoming, field in fields.items():
            if incoming in request.data:
                setattr(
                    item,
                    field,
                    request.data[incoming],
                )
                changed.append(field)

        if changed:
            item.save(update_fields=changed + ["updated_at"])

        return Response(
            {
                "id": item.id,
                "name": item.name,
                "unit": item.unit,
                "stock": decimal_value(item.quantity),
                "low_stock_threshold":
                    decimal_value(item.reorder_level),
            }
        )

    def delete(self, request, ingredient_id):
        item, error = self.get_object(
            request,
            ingredient_id,
        )

        if error:
            return error

        item.is_active = False
        item.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        return Response(status=204)