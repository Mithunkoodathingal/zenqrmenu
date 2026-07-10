# restaurant/services/common.py

from datetime import timezone

from django.shortcuts import get_object_or_404

from restaurant.models import (
    KitchenNote,
    OrderItem,
    Restaurant,
    Staff,
    Order,
    StaffAttendance,
    StaffBreak,
    Table,
    DeliveryPartner,
    StaffShiftSchedule,
    FoodItem,
    Category,
    AddOn,
)


# ==========================================================
# Restaurant
# ==========================================================

def get_restaurant(request):
    """
    Return the authenticated user's restaurant.
    """

    return get_object_or_404(
        Restaurant,
        owner=request.user,
    )

# ==========================================================
# Staff
# ==========================================================

def get_staff(
    *,
    restaurant,
    staff_id,
):
    """
    Return a staff member belonging to a restaurant.
    """

    return get_object_or_404(
        Staff,
        id=staff_id,
        restaurant=restaurant,
        is_deleted=False,
    )

# ==========================================================
# Staff By User
# ==========================================================

def get_staff_by_user(
    *,
    restaurant,
    user,
):
    """
    Return the logged-in staff member.
    """

    return get_object_or_404(
        Staff,
        restaurant=restaurant,
        user=user,
        is_deleted=False,
    )

# ==========================================================
# Order
# ==========================================================

def get_order(
    *,
    restaurant,
    order_id,
):
    """
    Return an order belonging to a restaurant.
    """

    return get_object_or_404(
        Order,
        id=order_id,
        restaurant=restaurant,
        is_deleted=False,
    )

# ==========================================================
# Table
# ==========================================================

def get_table(
    *,
    restaurant,
    table_id,
):
    """
    Return a restaurant table.
    """

    return get_object_or_404(
        Table,
        id=table_id,
        restaurant=restaurant,
    )

# ==========================================================
# Delivery Partner
# ==========================================================

def get_delivery_partner(
    *,
    restaurant,
    partner_id,
):
    """
    Return a delivery partner.
    """

    return get_object_or_404(
        DeliveryPartner,
        id=partner_id,
        restaurant=restaurant,
    )

# ==========================================================
# Food Item
# ==========================================================

def get_food_item(
    *,
    restaurant,
    food_item_id,
):
    """
    Return a food item.
    """

    return get_object_or_404(
        FoodItem,
        id=food_item_id,
        restaurant=restaurant,
    )

# ==========================================================
# Category
# ==========================================================

def get_category(
    *,
    restaurant,
    category_id,
):
    """
    Return a food category.
    """

    return get_object_or_404(
        Category,
        id=category_id,
        restaurant=restaurant,
    )

# ==========================================================
# Add-On
# ==========================================================

def get_addon(
    *,
    addon_id,
):
    """
    Return an add-on.
    """

    return get_object_or_404(
        AddOn,
        id=addon_id,
    )
    
# ==========================================================
# Order Item
# ==========================================================

def get_order_item(
    *,
    order,
    order_item_id,
):
    """
    Return an order item belonging to an order.
    """

    return get_object_or_404(
        OrderItem,
        id=order_item_id,
        order=order,
    )

# ==========================================================
# Kitchen Note
# ==========================================================

def get_kitchen_note(
    *,
    restaurant,
    note_id,
):
    return get_object_or_404(
        KitchenNote,
        id=note_id,
        order__restaurant=restaurant,
        is_deleted=False,
    )

# ==========================================================
# Staff Attendance
# ==========================================================

def get_staff_attendance(
    *,
    attendance_id,
):
    """
    Return a staff attendance record.
    """

    return get_object_or_404(
        StaffAttendance,
        id=attendance_id,
        is_deleted=False,
    )

# ==========================================================
# Shift Schedule
# ==========================================================

def get_shift_schedule(
    *,
    schedule_id,
):
    """
    Return a staff shift schedule.
    """

    return get_object_or_404(
        StaffShiftSchedule,
        id=schedule_id,
        is_deleted=False,
    )

# ==========================================================
# Get User Restaurant
# ==========================================================
    
def get_user_restaurant(user):
    return Restaurant.objects.filter(owner=user).first()


# ===============================================================================================================
# ===============================================================================================================
#                                           Context-Aware Helpers
# ===============================================================================================================
# ===============================================================================================================


# ==========================================================
# Today's Attendance
# ==========================================================

def get_today_attendance(
    *,
    restaurant,
    staff,
):
    """
    Return today's attendance record for a staff member.
    """

    return get_object_or_404(
        StaffAttendance,
        restaurant=restaurant,
        staff=staff,
        attendance_date=timezone.localdate(),
        is_deleted=False,
    )
    
# ==========================================================
# Current Shift Schedule
# ==========================================================

def get_current_shift_schedule(
    *,
    restaurant,
    staff,
):
    """
    Return today's shift schedule.
    """

    weekday = timezone.localdate().strftime("%A").lower()

    return get_object_or_404(
        StaffShiftSchedule,
        restaurant=restaurant,
        staff=staff,
        day_of_week=weekday,
        is_active=True,
        is_deleted=False,
    )
    
# ==========================================================
# Active Order
# ==========================================================

def get_active_order(
    *,
    restaurant,
    order_id,
):
    """
    Return an active order.
    """

    return get_object_or_404(
        Order,
        id=order_id,
        restaurant=restaurant,
        is_deleted=False,
        is_completed=False,
    )
    
# ==========================================================
# Active Break
# ==========================================================

def get_active_break(
    *,
    attendance,
):
    """
    Return the currently active break.
    """

    return get_object_or_404(
        StaffBreak,
        attendance=attendance,
        is_active=True,
    )
    
# ==========================================================
# Current Active Break
# ==========================================================

def get_current_active_break(
    *,
    attendance,
):
    """
    Return the active break if one exists.
    
    Then you can choose the appropriate helper:

    get_active_break() → Use when an active break must exist (e.g., ending a break).
    get_current_active_break() → Use when an active break is optional (e.g., checking whether a staff member is currently on break).

    This gives you flexibility while keeping the intent of each call clear.
    
    """

    return (
        StaffBreak.objects.filter(
            attendance=attendance,
            is_active=True,
        )
        .select_related("attendance")
        .first()
    )
    
    
    
