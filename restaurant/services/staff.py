
from django.shortcuts import get_object_or_404

from datetime import timezone

from rest_framework import request

from restaurant.models import Staff
from restaurant.services.common import get_staff_by_user


#                           # =============================================================================
                            # =============================================================================

                            # ---------------------------- STAFF SERVICES ---------------------------------

                            # =============================================================================
#                           # =============================================================================

# =============================================================================
# Clock In
# =============================================================================

def clock_in(staff):
    """
    Marks a staff member as
    on shift.
    """

    if staff.is_deleted:

        raise ValueError(
            "Cannot clock in a deleted staff member."
        )

    if not staff.is_active:

        raise ValueError(
            "Cannot clock in an inactive staff member."
        )

    now = timezone.now()

    staff.is_on_shift = True

    staff.is_on_break = False

    staff.last_shift_started_at = now

    staff.save(
        update_fields=[
            "is_on_shift",
            "is_on_break",
            "last_shift_started_at",
        ]
    )

    return staff


# =============================================================================
# Clock Out
# =============================================================================

def clock_out(staff):
    """
    Marks a staff member as
    off shift.
    """

    if not staff.is_on_shift:

        return staff

    now = timezone.now()

    staff.is_on_shift = False

    staff.is_on_break = False

    staff.last_shift_ended_at = now

    staff.save(
        update_fields=[
            "is_on_shift",
            "is_on_break",
            "last_shift_ended_at",
        ]
    )

    return staff

# =============================================================================
# Start Break
# =============================================================================

def start_break(staff):
    """
    Starts staff break.
    """

    if not staff.is_on_shift:

        raise ValueError(
            "Staff is not on shift."
        )

    staff.is_on_break = True

    staff.save(
        update_fields=[
            "is_on_break",
        ]
    )

    return staff

# =============================================================================
# End Break
# =============================================================================

def end_break(staff):
    """
    Ends staff break.
    """

    if not staff.is_on_shift:

        raise ValueError(
            "Staff is not on shift."
        )

    staff.is_on_break = False

    staff.save(
        update_fields=[
            "is_on_break",
        ]
    )

    return staff

# =============================================================================
# Change Role
# =============================================================================

def change_role(
    staff,
    role,
):
    """
    Updates staff role.
    """

    valid_roles = [

        "owner",

        "manager",

        "chef",

        "cashier",

        "waiter",

        "delivery_manager",

        "inventory_manager",

    ]

    if role not in valid_roles:

        raise ValueError(
            "Invalid role."
        )

    staff.role = role

    staff.save(
        update_fields=[
            "role",
        ]
    )

    return staff

# =============================================================================
# Staff Statistics
# =============================================================================

def staff_statistics(
    restaurant,
):
    """
    Returns staff dashboard
    statistics.
    """


    queryset = Staff.objects.filter(
        restaurant=restaurant,
        is_deleted=False,
    )
    
    stats = {
        "total_staff": queryset.count(),
        "active_staff": queryset.filter(is_active=True).count(),
        "inactive_staff": queryset.filter(is_active=False).count(),
        "on_shift": queryset.filter(is_on_shift=True).count(),
        "on_break": queryset.filter(is_on_break=True).count(),
    }

    for role, _ in Staff.ROLE_CHOICES:
        
        stats[f"{role}_count"] = queryset.filter(role=role).count()

    return stats
    
# =============================================================================
# update shift schedule
# =============================================================================
   
def update_shift_schedule(
    staff,
    shift_start,
    shift_end,
):
    
    """
    Updates the planned working
    shift schedule of a staff member.
    """

    staff.shift_start = shift_start

    staff.shift_end = shift_end

    staff.save(

        update_fields=[

            "shift_start",

            "shift_end",

        ]

    )

    return staff


# ============================================================================
# Staff Role Services
# ============================================================================


def get_staff_role(
    *,
    restaurant,
    staff_id,
):
    """
    Return the current role of a staff member.
    """

    return get_object_or_404(
        Staff,
        id=staff_id,
        restaurant=restaurant,
        is_deleted=False,
    )

# =============================================================================
# update Staff Role
# =============================================================================

def update_staff_role(
    *,
    restaurant,
    staff_id,
    role,
):
    """
    Update the role of a staff member.
    """

    staff = get_staff_by_user(
        restaurant=restaurant,
        user=request.user,
    )

    staff.role = role
    staff.save(update_fields=["role"])

    return staff

