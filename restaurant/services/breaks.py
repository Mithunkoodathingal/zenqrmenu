# restaurants/services/breaks.py

from django.shortcuts import get_object_or_404
from django.utils import timezone

from restaurant.models import (
    StaffAttendance,
    StaffBreak,
)

from restaurant.services.common import (
    get_staff,
    get_today_attendance,
)


# ==========================================================
# Start Break
# ==========================================================

def start_break(
    *,
    restaurant,
    staff_id,
):
    """
    Start a staff break.
    """

    staff = get_staff(
        restaurant=restaurant,
        staff_id=staff_id,
    )

    attendance = get_today_attendance(
        restaurant=restaurant,
        staff=staff,
    )

    active_break = StaffBreak.objects.filter(
        attendance=attendance,
        is_active=True,
    ).exists()

    if active_break:
        raise ValueError(
            "Staff already has an active break."
        )

    staff_break = StaffBreak.objects.create(
        attendance=attendance,
        break_start=timezone.now(),
    )

    staff.is_on_break = True

    staff.save(
        update_fields=[
            "is_on_break",
        ]
    )

    return staff_break


# ==========================================================
# End Break
# ==========================================================

def end_break(
    *,
    restaurant,
    staff_id,
):
    """
    End the active break.
    """

    staff = get_staff(
        restaurant=restaurant,
        staff_id=staff_id,
    )

    attendance = get_today_attendance(
        restaurant=restaurant,
        staff=staff,
    )

    staff_break = get_object_or_404(
        StaffBreak,
        attendance=attendance,
        is_active=True,
    )

    now = timezone.now()

    staff_break.break_end = now

    staff_break.minutes = int(
        (
            now - staff_break.break_start
        ).total_seconds() // 60
    )

    staff_break.is_active = False

    staff_break.save(
        update_fields=[
            "break_end",
            "minutes",
            "is_active",
        ]
    )

    attendance.break_minutes += staff_break.minutes

    attendance.save(
        update_fields=[
            "break_minutes",
        ]
    )

    staff.is_on_break = False

    staff.save(
        update_fields=[
            "is_on_break",
        ]
    )

    return staff_break


# ==========================================================
# Get Breaks
# ==========================================================

def get_breaks(
    *,
    restaurant,
    attendance_id=None,
    staff_id=None,
    today=False,
):
    """
    Return staff break history.
    """

    queryset = StaffBreak.objects.filter(
        attendance__restaurant=restaurant,
    )

    if attendance_id:

        queryset = queryset.filter(
            attendance_id=attendance_id,
        )

    if staff_id:

        queryset = queryset.filter(
            attendance__staff_id=staff_id,
        )

    if today:

        queryset = queryset.filter(
            attendance__attendance_date=timezone.localdate(),
        )

    return queryset.select_related(
        "attendance",
        "attendance__staff",
    ).order_by(
        "-break_start",
    )
    
    
