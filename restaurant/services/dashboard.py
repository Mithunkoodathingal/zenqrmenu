# # restaurant/services/dashboard.py


from restaurant.services.analytics import (
    get_sales_statistics,
    get_staff_statistics,
    get_delivery_statistics,
)
from restaurant.services.analytics import (
    get_dashboard_cards,
    get_sales_chart,
)
from restaurant.services.queries import get_recent_orders
from restaurant.services.restaurant import (
    get_kitchen_statistics,
)

def get_dashboard_data(restaurant):
    return {
        "cards": get_dashboard_cards(restaurant),
        "sales": get_sales_statistics(restaurant=restaurant),
        "staff": get_staff_statistics(restaurant=restaurant),
        "delivery": get_delivery_statistics(restaurant=restaurant),
        "kitchen": get_kitchen_statistics(restaurant=restaurant),
        "recent_orders": get_recent_orders(restaurant),
        "sales_chart": get_sales_chart(restaurant),
    }
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

# from django.db.models import Sum

# from datetime import timedelta, timezone

# from restaurant.models import DeliveryPartner, FoodItem, Order, OrderItem




# #                           # =============================================================================
#                             # =============================================================================

#                             # ----------------------------- DASHBOARD HELPERS ----------------------------

#                             # =============================================================================
# #                           # =============================================================================


# # =============================================================================
# # Dashboard Cards
# # =============================================================================

# def get_dashboard_cards(
#     restaurant,
# ):
#     """
#     Returns dashboard summary cards.
#     """

#     today = timezone.localdate()

#     month_start = today.replace(
#         day=1,
#     )

#     # ==========================================================
#     # Base Querysets
#     # ==========================================================

#     orders = Order.objects.filter(

#         restaurant=restaurant,

#         is_deleted=False,

#     )

#     today_orders = orders.filter(

#         created_at__date=today,

#     )

#     month_orders = orders.filter(

#         created_at__date__gte=month_start,

#     )

#     # ==========================================================
#     # Sales
#     # ==========================================================

#     today_sales = (

#         today_orders.filter(
#             payment_status="paid",
#         )

#         .aggregate(
#             total=Sum("grand_total")
#         )["total"]

#         or 0

#     )

#     monthly_sales = (

#         month_orders.filter(
#             payment_status="paid",
#         )

#         .aggregate(
#             total=Sum("grand_total")
#         )["total"]

#         or 0

#     )

#     # ==========================================================
#     # Orders
#     # ==========================================================

#     pending_orders = orders.filter(

#         status="pending",

#     ).count()

#     active_orders = orders.filter(

#         status__in=[

#             "confirmed",

#             "preparing",

#             "ready",

#         ]

#     ).count()

#     total_orders = orders.count()

#     customers_today = (

#         today_orders.values(
#             "customer_phone"
#         )

#         .distinct()

#         .count()

#     )

#     # ==========================================================
#     # Delivery Partners
#     # ==========================================================

#     delivery_online = DeliveryPartner.objects.filter(

#         restaurant=restaurant,

#         is_active=True,

#         is_available=True,

#     ).count()

#     # ==========================================================
#     # Kitchen
#     # ==========================================================

#     kitchen_pending = orders.filter(

#         kitchen_printed=False,

#         status__in=[

#             "pending",

#             "confirmed",

#             "preparing",

#         ],

#     ).count()

#     # ==========================================================
#     # Refunds
#     # ==========================================================

#     refunds_today = orders.filter(

#         payment_status="refunded",

#         created_at__date=today,

#     ).count()

#     # ==========================================================
#     # Coupons
#     # ==========================================================

#     #
#     # Replace later with Coupon model
#     #

#     coupons_used = 0

#     # ==========================================================
#     # Inventory Alerts
#     # ==========================================================

#     #
#     # Replace later with Inventory model
#     #

#     inventory_alerts = FoodItem.objects.filter(

#         restaurant=restaurant,

#         is_paused=True,

#     ).count()

#     # ==========================================================
#     # Return
#     # ==========================================================

#     return {

#         "today_sales": today_sales,

#         "monthly_sales": monthly_sales,

#         "pending_orders": pending_orders,

#         "active_orders": active_orders,

#         "total_orders": total_orders,

#         "customers_today": customers_today,

#         "delivery_partners_online": delivery_online,

#         "kitchen_pending": kitchen_pending,

#         "refunds_today": refunds_today,

#         "coupons_used": coupons_used,

#         "inventory_alerts": inventory_alerts,

#     }
    
# # =============================================================================
# # Recent Orders
# # =============================================================================

# def get_recent_orders(
#     restaurant,
#     limit=10,
# ):
#     """
#     Returns recent restaurant orders.
#     """

#     queryset = (

#         Order.objects

#         .filter(

#             restaurant=restaurant,

#             is_deleted=False,

#         )

#         .select_related(

#             "table",

#             "delivery_partner",

#         )

#         .order_by(

#             "-created_at",

#         )[:limit]

#     )

#     results = []

#     for order in queryset:

#         results.append(

#             {

#                 "id": order.id,

#                 "order_number": order.order_number,

#                 "customer_name": order.customer_name,

#                 "customer_phone": order.customer_phone,

#                 "order_type": order.order_type,

#                 "status": order.status,

#                 "payment_status": order.payment_status,

#                 "delivery_status": order.delivery_status,

#                 "grand_total": float(

#                     order.grand_total

#                 ),

#                 "created_at": order.created_at,

#                 "table": (

#                     order.table.table_number

#                     if order.table

#                     else None

#                 ),

#                 "delivery_partner": (

#                     order.delivery_partner.full_name

#                     if order.delivery_partner

#                     else None

#                 ),

#             }

#         )

#     return results

# # =============================================================================
# # Top Selling Items
# # =============================================================================

# def get_top_selling_items(
#     restaurant,
#     limit=10,
# ):
#     """
#     Returns the best selling menu items.
#     """

#     queryset = (

#         OrderItem.objects

#         .filter(

#             order__restaurant=restaurant,

#             order__is_deleted=False,

#             order__payment_status="paid",

#         )

#         .values(

#             "food_item",

#             "food_item__name",

#         )

#         .annotate(

#             total_quantity=Sum("quantity"),

#         )

#         .order_by(

#             "-total_quantity",

#         )[:limit]

#     )

#     results = []

#     for item in queryset:

#         results.append(

#             {

#                 "food_item_id": item["food_item"],

#                 "name": item["food_item__name"],

#                 "quantity_sold": item["total_quantity"],

#             }

#         )

#     return results

# # =============================================================================
# # Sales Chart
# # =============================================================================

# def get_sales_chart(
#     restaurant,
#     days=30,
#     group_by="day",
# ):
#     """
#     Returns sales chart data.

#     Parameters
#     ----------
#     days : int
#         Number of days to include.

#     group_by : str
#         Future support for:
#         - day
#         - week
#         - month
#         - year
#     """

#     today = timezone.localdate()

#     start_date = today - timedelta(days=days - 1)

#     queryset = (

#         Order.objects

#         .filter(

#             restaurant=restaurant,

#             is_deleted=False,

#             payment_status="paid",

#             created_at__date__gte=start_date,

#         )

#         .values(

#             "created_at__date",

#         )

#         .annotate(

#             sales=Sum("grand_total"),

#         )

#     )

#     sales_lookup = {

#         row["created_at__date"]: float(
#             row["sales"] or 0
#         )

#         for row in queryset

#     }

#     chart = []

#     current = start_date

#     while current <= today:

#         chart.append(

#             {

#                 "date": current.strftime(
#                     "%d %b"
#                 ),

#                 "sales": sales_lookup.get(
#                     current,
#                     0,
#                 ),

#             }

#         )

#         current += timedelta(
#             days=1,
#         )

#     return chart

# # =============================================================================
# # Dashboard Data
# # =============================================================================

# def get_dashboard_data(
#     restaurant,
# ):
#     """
#     Returns the complete dashboard payload.

#     This is the primary service used by
#     DashboardAPIView.

#     Includes

#     • Dashboard cards

#     • Recent orders

#     • Top selling items

#     • Sales chart

#     Future

#     • Revenue chart

#     • Order summary

#     • Kitchen metrics

#     • Delivery analytics

#     • Refund analytics

#     • Customer analytics
#     """

#     # ==========================================================
#     # Dashboard Cards
#     # ==========================================================

#     cards = get_dashboard_cards(
#         restaurant
#     )

#     # ==========================================================
#     # Recent Orders
#     # ==========================================================

#     recent_orders = get_recent_orders(
#         restaurant
#     )

#     # ==========================================================
#     # Top Selling Items
#     # ==========================================================

#     top_selling_items = get_top_selling_items(
#         restaurant
#     )

#     # ==========================================================
#     # Sales Chart
#     # ==========================================================

#     sales_chart = get_sales_chart(
#         restaurant,
#     )

#     # ==========================================================
#     # Return
#     # ==========================================================

#     return {

#         "cards": cards,

#         "recent_orders": recent_orders,

#         "top_selling_items": top_selling_items,

#         "sales_chart": sales_chart,

#         # ======================================================
#         # Future Modules
#         # ======================================================

#         "revenue_chart": [],

#         "order_summary": {},

#         "kitchen": {},

#         "delivery": {},

#         "refunds": {},

#         "customers": {},

#     }
    