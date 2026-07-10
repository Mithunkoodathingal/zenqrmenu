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
"""
restaurant/services.py

Delivery Partner Services
"""

from django.db import transaction

from django.utils import timezone

from django.db.models import F, Avg, DurationField, ExpressionWrapper, Sum

from django.shortcuts import get_object_or_404

from ..models import (
    
    FoodItem,
    
    KitchenNote,
    
    Order,
    
    DeliveryPartner,
    
    OrderItem,
    
    Staff,
    
    StaffAttendance,
    
)

from datetime import date

from django.db.models import Count

from datetime import timedelta

from decimal import Decimal

from math import radians, sin, cos, sqrt, atan2

from django.core.exceptions import ValidationError



# #                           # =============================================================================
#                             # =============================================================================

#                             # ----------------------------- DELIVERY HELPERS ------------------------------

#                             # =============================================================================
# #                           # =============================================================================

# # ==========================================================
# # Distance Helpers
# # ==========================================================

# def calculate_distance(
#     latitude1,
#     longitude1,
#     latitude2,
#     longitude2,
# ):
#     """
#     Calculate distance between two GPS coordinates.

#     Returns
#     -------
#     Decimal
#         Distance in kilometers.
#     """

#     if None in (
#         latitude1,
#         longitude1,
#         latitude2,
#         longitude2,
#     ):
#         return Decimal("0.00")

#     earth_radius = 6371.0

#     lat1 = radians(float(latitude1))
#     lon1 = radians(float(longitude1))

#     lat2 = radians(float(latitude2))
#     lon2 = radians(float(longitude2))

#     delta_lat = lat2 - lat1
#     delta_lon = lon2 - lon1

#     a = (
#         sin(delta_lat / 2) ** 2
#         + cos(lat1)
#         * cos(lat2)
#         * sin(delta_lon / 2) ** 2
#     )

#     c = 2 * atan2(
#         sqrt(a),
#         sqrt(1 - a),
#     )

#     distance = earth_radius * c

#     return Decimal(str(round(distance, 2)))

# # ==========================================================
# # Coverage
# # ==========================================================

# def is_inside_delivery_radius(
#     restaurant,
#     customer_latitude,
#     customer_longitude,
# ):
#     """
#     Returns True if the customer lies inside
#     the restaurant's delivery radius.
#     """

#     distance = calculate_distance(

#         restaurant.delivery_latitude,

#         restaurant.delivery_longitude,

#         customer_latitude,

#         customer_longitude,

#     )

#     return (

#         distance <= restaurant.maximum_delivery_radius_km,

#         distance,

#     )
    
# # ==========================================================
# # Delivery Charges
# # ==========================================================

# def calculate_delivery_charge(
#     restaurant,
#     distance,
# ):
#     """
#     Calculates delivery charge based on distance.
#     """

#     if distance <= restaurant.free_delivery_radius_km:

#         return Decimal("0.00")

#     extra_distance = (

#         distance
#         - restaurant.free_delivery_radius_km

#     )

#     return (

#         extra_distance
#         * restaurant.delivery_charge_per_km

#     ).quantize(Decimal("0.01"))
    
# # ==========================================================
# # Delivery Validation
# # ==========================================================

# def validate_delivery(
#     restaurant,
#     order,
# ):
#     """
#     Validates whether an order
#     can be delivered.
#     """

#     if not restaurant.delivery_enabled:

#         raise ValidationError(
#             "Delivery is disabled."
#         )

#     inside, distance = is_inside_delivery_radius(

#         restaurant,

#         order.delivery_latitude,

#         order.delivery_longitude,

#     )

#     if not inside:

#         raise ValidationError(
#             "Customer is outside delivery radius."
#         )

#     if (

#         order.total_price_cached
#         < restaurant.minimum_delivery_order

#     ):

#         raise ValidationError(

#             "Minimum order amount not reached."

#         )

#     charge = calculate_delivery_charge(

#         restaurant,

#         distance,

#     )

#     return {

#         "distance": distance,

#         "delivery_charge": charge,

#     }

# # ==========================================================
# # Delivery Time
# # ==========================================================

# def estimate_delivery_time(
#     restaurant,
#     distance,
# ):
#     """
#     Returns estimated delivery time.

#     Uses average speed of 30 km/h.
#     """

#     average_speed = Decimal("30")

#     travel_minutes = (

#         distance / average_speed

#     ) * Decimal("60")

#     total = (

#         Decimal(restaurant.average_preparation_time)

#         + travel_minutes

#     )

#     return int(total)

# # ==========================================================
# # Delivery Summary
# # ==========================================================

# def get_delivery_summary(
#     restaurant,
#     latitude,
#     longitude,
# ):
#     """
#     Returns delivery information
#     for a customer location.
#     """

#     inside, distance = is_inside_delivery_radius(

#         restaurant,

#         latitude,

#         longitude,

#     )

#     charge = calculate_delivery_charge(

#         restaurant,

#         distance,

#     )

#     eta = estimate_delivery_time(

#         restaurant,

#         distance,

#     )

#     return {

#         "can_deliver": inside,

#         "distance_km": distance,

#         "delivery_charge": charge,

#         "estimated_minutes": eta,

#         "free_delivery": (

#             charge == Decimal("0.00")

#         ),

#     }
       
# # ==========================================================
# # Nearby Restaurants
# # ==========================================================

# def nearby_restaurants(
#     restaurants,
#     latitude,
#     longitude,
# ):
#     """
#     Filters restaurants capable
#     of delivering to the customer.

#     Returns a list sorted by distance.
#     """

#     results = []

#     for restaurant in restaurants:

#         inside, distance = is_inside_delivery_radius(

#             restaurant,

#             latitude,

#             longitude,

#         )

#         if inside:

#             results.append(

#                 {

#                     "restaurant": restaurant,

#                     "distance": distance,

#                 }

#             )

#     results.sort(

#         key=lambda item: item["distance"]

#     )

#     return results

# #                           # =============================================================================
#                             # =============================================================================

#                             # ----------------------------- DELIVERY PARTNER HELPERS ---------------------

#                             # =============================================================================
# #                           # =============================================================================


# # =============================================================================
# # Assign Delivery Partner
# # =============================================================================

# @transaction.atomic
# def assign_delivery_partner(
#     order: Order,
#     partner: DeliveryPartner,
# ):
#     """
#     Assign a delivery partner to an order.

#     Parameters
#     ----------
#     order : Order

#     partner : DeliveryPartner

#     Returns
#     -------
#     Order
#     """

#     if order.order_type != "delivery":
#         raise ValueError(
#             "Only delivery orders can be assigned."
#         )

#     if order.delivery_partner:
#         raise ValueError(
#             "Delivery partner already assigned."
#         )

#     if not partner.is_active:
#         raise ValueError(
#             "Delivery partner is inactive."
#         )

#     if not partner.is_available:
#         raise ValueError(
#             "Delivery partner is unavailable."
#         )

#     order.delivery_partner = partner

#     order.delivery_status = "assigned"

#     order.assigned_at = timezone.now()

#     order.save(
#         update_fields=[
#             "delivery_partner",
#             "delivery_status",
#             "assigned_at",
#         ]
#     )

#     partner.is_available = False

#     partner.save(
#         update_fields=[
#             "is_available",
#         ]
#     )

#     return order

# # =============================================================================
# # Unassign Delivery Partner
# # =============================================================================

# @transaction.atomic
# def unassign_delivery_partner(
#     order: Order,
# ):
#     """
#     Remove a delivery partner from an order.

#     Parameters
#     ----------
#     order : Order

#     Returns
#     -------
#     Order
#     """

#     if order.delivery_partner is None:
#         raise ValueError(
#             "No delivery partner assigned."
#         )

#     if order.delivery_status == "delivered":
#         raise ValueError(
#             "Delivered orders cannot be unassigned."
#         )

#     partner = order.delivery_partner

#     partner.is_available = True

#     partner.save(
#         update_fields=[
#             "is_available",
#         ]
#     )

#     order.delivery_partner = None

#     order.delivery_status = "not_required"

#     order.assigned_at = None

#     order.picked_at = None

#     order.delivered_at = None

#     order.save(
#         update_fields=[
#             "delivery_partner",
#             "delivery_status",
#             "assigned_at",
#             "picked_at",
#             "delivered_at",
#         ]
#     )

#     return order

# # =============================================================================
# # Update Delivery Status
# # =============================================================================

# @transaction.atomic
# def update_delivery_status(
#     order: Order,
#     status: str,
# ):
#     """
#     Update delivery status.

#     Valid transitions:

#         assigned
#             ↓

#         picked
#             ↓

#         out_for_delivery
#             ↓

#         delivered

#     Returns
#     -------
#     Order
#     """

#     valid_statuses = [

#         "pending",

#         "assigned",

#         "picked",

#         "out_for_delivery",

#         "delivered",

#         "failed",

#         "cancelled",

#     ]

#     if status not in valid_statuses:

#         raise ValueError(
#             "Invalid delivery status."
#         )

#     order.delivery_status = status

#     now = timezone.now()

#     if status == "assigned":

#         order.assigned_at = now

#     elif status == "picked":

#         order.picked_at = now

#     elif status == "delivered":

#         order.delivered_at = now

#         if order.delivery_partner:

#             partner = order.delivery_partner

#             partner.is_available = True

#             partner.total_deliveries += 1

#             partner.save(
#                 update_fields=[
#                     "is_available",
#                     "total_deliveries",
#                 ]
#             )

#     order.save()

#     return order

# # =============================================================================
# # Update Partner Location
# # =============================================================================

# @transaction.atomic
# def update_partner_location(
#     partner: DeliveryPartner,
#     latitude,
#     longitude,
# ):
#     """
#     Update live GPS coordinates
#     of a delivery partner.
#     """

#     latitude = float(latitude)

#     longitude = float(longitude)

#     if latitude < -90 or latitude > 90:
#         raise ValueError(
#             "Latitude must be between -90 and 90."
#         )

#     if longitude < -180 or longitude > 180:
#         raise ValueError(
#             "Longitude must be between -180 and 180."
#         )

#     partner.current_latitude = latitude

#     partner.current_longitude = longitude

#     partner.save(
#         update_fields=[
#             "current_latitude",
#             "current_longitude",
#         ]
#     )

#     return partner

# # =============================================================================
# # Get Delivery Tracking
# # =============================================================================

# def get_delivery_tracking(
#     order: Order,
# ):
#     """
#     Return delivery tracking information
#     for an order.

#     This helper is intentionally independent
#     of DRF serializers so it can be reused by:

#     • Customer Tracking API
#     • Restaurant Dashboard
#     • Delivery Partner App
#     • Admin Dashboard
#     • Notifications
#     """

#     partner = order.delivery_partner

#     # ==========================================================
#     # Delivery Partner
#     # ==========================================================

#     partner_data = None

#     if partner:

#         partner_data = {

#             "id": partner.id,

#             "name": (
#                 f"{partner.first_name} {partner.last_name}".strip()
#             ),

#             "full_name": partner.full_name,

#             "phone": partner.phone,

#             "photo": (
#                 partner.profile_photo.url
#                 if partner.profile_photo
#                 else None
#             ),

#             "vehicle_type": partner.vehicle_type,

#             "vehicle_number": partner.vehicle_number,

#             "rating": float(
#                 partner.average_rating or 0
#             ),

#             "completed_orders": (
#                 partner.total_deliveries
#             ),

#             "successful_deliveries": (
#                 partner.successful_deliveries
#             ),

#             "cancelled_deliveries": (
#                 partner.cancelled_deliveries
#             ),

#             "is_available": (
#                 partner.is_available
#             ),

#             "is_active": (
#                 partner.is_active
#             ),

#             "current_location": {

#                 "latitude": (
#                     float(partner.current_latitude)
#                     if partner.current_latitude is not None
#                     else None
#                 ),

#                 "longitude": (
#                     float(partner.current_longitude)
#                     if partner.current_longitude is not None
#                     else None
#                 ),

#             },

#         }

#     # ==========================================================
#     # ETA
#     # ==========================================================

#     eta = None

#     if order.delivered_at:

#         eta = order.delivered_at

#     elif order.picked_at:

#         eta = (
#             order.picked_at
#             + timezone.timedelta(minutes=20)
#         )

#     elif order.assigned_at:

#         eta = (
#             order.assigned_at
#             + timedelta(
#                 minutes=order.restaurant.average_preparation_time
#             )
#             + timedelta(
#                 minutes=int(float(order.delivery_distance_km) * 3)
#             )
#         )

#     # ==========================================================
#     # Response
#     # ==========================================================

#     return {

#         "order_id": order.id,

#         "order_number": order.order_number,

#         "order_status": order.status,

#         "delivery_status": order.delivery_status,

#         "delivery_partner": partner_data,

#         "assigned_at": order.assigned_at,

#         "picked_at": order.picked_at,

#         "delivered_at": order.delivered_at,

#         "estimated_delivery_time": eta,

#         "delivery_distance_km": (
#             float(order.delivery_distance_km)
#             if order.delivery_distance_km is not None
#             else None
#         ),

#         "delivery_charge": (
#             float(order.delivery_charge)
#             if order.delivery_charge is not None
#             else None
#         ),

#         "customer_location": {

#             "latitude": (
#                 float(order.delivery_latitude)
#                 if order.delivery_latitude is not None
#                 else None
#             ),

#             "longitude": (
#                 float(order.delivery_longitude)
#                 if order.delivery_longitude is not None
#                 else None
#             ),

#             "address": order.delivery_address,

#             "landmark": order.customer_address,

#             "pincode": order.customer_pincode,

#         },

#     }
     
# # =============================================================================
# # Update Partner Availability
# # =============================================================================

# @transaction.atomic
# def update_partner_availability(
#     partner: DeliveryPartner,
#     is_available: bool,
# ):
#     """
#     Update the availability status of
#     a delivery partner.
#     """

#     partner.is_available = is_available

#     partner.save(
#         update_fields=[
#             "is_available",
#         ]
#     )

#     return partner


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
    
# #                           # =============================================================================
#                             # =============================================================================

#                             # ---------------------------- STAFF SERVICES ---------------------------------

#                             # =============================================================================
# #                           # =============================================================================

# # =============================================================================
# # Clock In
# # =============================================================================

# def clock_in(staff):
#     """
#     Marks a staff member as
#     on shift.
#     """

#     if staff.is_deleted:

#         raise ValueError(
#             "Cannot clock in a deleted staff member."
#         )

#     if not staff.is_active:

#         raise ValueError(
#             "Cannot clock in an inactive staff member."
#         )

#     now = timezone.now()

#     staff.is_on_shift = True

#     staff.is_on_break = False

#     staff.last_shift_started_at = now

#     staff.save(
#         update_fields=[
#             "is_on_shift",
#             "is_on_break",
#             "last_shift_started_at",
#         ]
#     )

#     return staff


# # =============================================================================
# # Clock Out
# # =============================================================================

# def clock_out(staff):
#     """
#     Marks a staff member as
#     off shift.
#     """

#     if not staff.is_on_shift:

#         return staff

#     now = timezone.now()

#     staff.is_on_shift = False

#     staff.is_on_break = False

#     staff.last_shift_ended_at = now

#     staff.save(
#         update_fields=[
#             "is_on_shift",
#             "is_on_break",
#             "last_shift_ended_at",
#         ]
#     )

#     return staff

# # =============================================================================
# # Start Break
# # =============================================================================

# def start_break(staff):
#     """
#     Starts staff break.
#     """

#     if not staff.is_on_shift:

#         raise ValueError(
#             "Staff is not on shift."
#         )

#     staff.is_on_break = True

#     staff.save(
#         update_fields=[
#             "is_on_break",
#         ]
#     )

#     return staff

# # =============================================================================
# # End Break
# # =============================================================================

# def end_break(staff):
#     """
#     Ends staff break.
#     """

#     if not staff.is_on_shift:

#         raise ValueError(
#             "Staff is not on shift."
#         )

#     staff.is_on_break = False

#     staff.save(
#         update_fields=[
#             "is_on_break",
#         ]
#     )

#     return staff

# # =============================================================================
# # Change Role
# # =============================================================================

# def change_role(
#     staff,
#     role,
# ):
#     """
#     Updates staff role.
#     """

#     valid_roles = [

#         "owner",

#         "manager",

#         "chef",

#         "cashier",

#         "waiter",

#         "delivery_manager",

#         "inventory_manager",

#     ]

#     if role not in valid_roles:

#         raise ValueError(
#             "Invalid role."
#         )

#     staff.role = role

#     staff.save(
#         update_fields=[
#             "role",
#         ]
#     )

#     return staff

# # =============================================================================
# # Staff Statistics
# # =============================================================================

# def staff_statistics(
#     restaurant,
# ):
#     """
#     Returns staff dashboard
#     statistics.
#     """


#     queryset = Staff.objects.filter(
#         restaurant=restaurant,
#         is_deleted=False,
#     )
    
#     stats = {
#         "total_staff": queryset.count(),
#         "active_staff": queryset.filter(is_active=True).count(),
#         "inactive_staff": queryset.filter(is_active=False).count(),
#         "on_shift": queryset.filter(is_on_shift=True).count(),
#         "on_break": queryset.filter(is_on_break=True).count(),
#     }

#     for role, _ in Staff.ROLE_CHOICES:
#         stats[f"{role}_count"] = queryset.filter(role=role).count()

#     return stats
    
# # =============================================================================
# # update shift schedule
# # =============================================================================
   
# def update_shift_schedule(
#     staff,
#     shift_start,
#     shift_end,
# ):
    
#     """
#     Updates the planned working
#     shift schedule of a staff member.
#     """

#     staff.shift_start = shift_start

#     staff.shift_end = shift_end

#     staff.save(

#         update_fields=[

#             "shift_start",

#             "shift_end",

#         ]

#     )

#     return staff


# # ============================================================================
# # Staff Role Services
# # ============================================================================


# def get_staff_role(
#     *,
#     restaurant,
#     staff_id,
# ):
#     """
#     Return the current role of a staff member.
#     """

#     return get_object_or_404(
#         Staff,
#         id=staff_id,
#         restaurant=restaurant,
#         is_deleted=False,
#     )

# # =============================================================================
# # update Staff Role
# # =============================================================================

# def update_staff_role(
#     *,
#     restaurant,
#     staff_id,
#     role,
# ):
#     """
#     Update the role of a staff member.
#     """

#     staff = get_object_or_404(
#         Staff,
#         id=staff_id,
#         restaurant=restaurant,
#         is_deleted=False,
#     )

#     staff.role = role
#     staff.save(update_fields=["role"])

#     return staff


# #                           # =============================================================================
#                             # =============================================================================

#                             # -----------------------------KDS HEALPER SERVICES---------------------------

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
    
    
# #                           # =============================================================================
#                             # =============================================================================

#                             # ----------------------------- ATTENDENCE MODULE -----------------------------

#                             # =============================================================================
# #                           # =============================================================================


# # ==========================================================
# # Clock In Staff
# # ==========================================================

# def clock_in_staff(
#     *,
#     restaurant,
#     staff_id,
# ):
#     """
#     Clock in a staff member.
#     """

#     staff = get_object_or_404(
#         Staff,
#         id=staff_id,
#         restaurant=restaurant,
#         is_deleted=False,
#     )

#     today = timezone.localdate()

#     attendance, created = StaffAttendance.objects.get_or_create(
#         restaurant=restaurant,
#         staff=staff,
#         attendance_date=today,
#         defaults={
#             "status": "present",
#             "clock_in": timezone.now(),
#         },
#     )

#     if not created and attendance.clock_in is None:
#         attendance.clock_in = timezone.now()
#         attendance.save(
#             update_fields=[
#                 "clock_in",
#             ]
#         )

#     staff.is_on_shift = True
#     staff.last_shift_started_at = timezone.now()

#     staff.save(
#         update_fields=[
#             "is_on_shift",
#             "last_shift_started_at",
#         ]
#     )

#     return attendance

# # ==========================================================
# # Clock Out Staff
# # ==========================================================

# def clock_out_staff(
#     *,
#     restaurant,
#     staff_id,
# ):
#     """
#     Clock out a staff member.
#     """

#     staff = get_object_or_404(
#         Staff,
#         id=staff_id,
#         restaurant=restaurant,
#         is_deleted=False,
#     )

#     attendance = get_object_or_404(
#         StaffAttendance,
#         restaurant=restaurant,
#         staff=staff,
#         attendance_date=timezone.localdate(),
#         is_deleted=False,
#     )

#     now = timezone.now()

#     attendance.clock_out = now

#     if attendance.clock_in:

#         worked_minutes = int(
#             (
#                 now - attendance.clock_in
#             ).total_seconds() // 60
#         )

#         attendance.worked_minutes = max(
#             worked_minutes - attendance.break_minutes,
#             0,
#         )

#     attendance.save(
#         update_fields=[
#             "clock_out",
#             "worked_minutes",
#         ]
#     )

#     staff.is_on_shift = False
#     staff.is_on_break = False
#     staff.last_shift_ended_at = now

#     staff.save(
#         update_fields=[
#             "is_on_shift",
#             "is_on_break",
#             "last_shift_ended_at",
#         ]
#     )

#     return attendance

# # ==========================================================
# # Get Staff Attendance
# # ==========================================================

# def get_staff_attendance(
#     *,
#     restaurant,
#     staff_id=None,
#     attendance_date=None,
# ):
#     """
#     Return attendance records.
#     """

#     queryset = StaffAttendance.objects.filter(
#         restaurant=restaurant,
#         is_deleted=False,
#     )

#     if staff_id:
#         queryset = queryset.filter(
#             staff_id=staff_id,
#         )

#     if attendance_date:
#         queryset = queryset.filter(
#             attendance_date=attendance_date,
#         )

#     return queryset.order_by(
#         "-attendance_date",
#         "-created_at",
#     )

# # ==========================================================
# # Update Attendance
# # ==========================================================

# def update_staff_attendance(
#     *,
#     restaurant,
#     attendance_id,
#     **validated_data,
# ):
#     """
#     Update attendance record.
#     """

#     attendance = get_object_or_404(
#         StaffAttendance,
#         id=attendance_id,
#         restaurant=restaurant,
#         is_deleted=False,
#     )

#     for field, value in validated_data.items():
#         setattr(
#             attendance,
#             field,
#             value,
#         )

#     attendance.save()

#     return attendance

# # ==========================================================
# # Attendance Statistics
# # ==========================================================

# def get_attendance_statistics(
#     *,
#     restaurant,
# ):
#     """
#     Attendance summary.
#     """

#     queryset = StaffAttendance.objects.filter(
#         restaurant=restaurant,
#         is_deleted=False,
#     )

#     return {

#         "total_records": queryset.count(),

#         "present": queryset.filter(
#             status="present",
#         ).count(),

#         "absent": queryset.filter(
#             status="absent",
#         ).count(),

#         "half_day": queryset.filter(
#             status="half_day",
#         ).count(),

#         "leave": queryset.filter(
#             status="leave",
#         ).count(),

#     }
    
    
