# restaurants/services/attendance.py


from datetime import timezone

from django.shortcuts import get_object_or_404

from restaurant.models import Staff, StaffAttendance




#                           # =============================================================================
                            # =============================================================================

                            # ----------------------------- ATTENDENCE MODULE -----------------------------

                            # =============================================================================
#                           # =============================================================================


# ==========================================================
# Clock In Staff
# ==========================================================

def clock_in_staff(
    *,
    restaurant,
    staff_id,
):
    """
    Clock in a staff member.
    """

    staff = get_object_or_404(
        Staff,
        id=staff_id,
        restaurant=restaurant,
        is_deleted=False,
    )

    today = timezone.localdate()

    attendance, created = StaffAttendance.objects.get_or_create(
        restaurant=restaurant,
        staff=staff,
        attendance_date=today,
        defaults={
            "status": "present",
            "clock_in": timezone.now(),
        },
    )

    if not created and attendance.clock_in is None:
        attendance.clock_in = timezone.now()
        attendance.save(
            update_fields=[
                "clock_in",
            ]
        )

    staff.is_on_shift = True
    staff.last_shift_started_at = timezone.now()

    staff.save(
        update_fields=[
            "is_on_shift",
            "last_shift_started_at",
        ]
    )

    return attendance

# ==========================================================
# Clock Out Staff
# ==========================================================

def clock_out_staff(
    *,
    restaurant,
    staff_id,
):
    """
    Clock out a staff member.
    """

    staff = get_object_or_404(
        Staff,
        id=staff_id,
        restaurant=restaurant,
        is_deleted=False,
    )

    attendance = get_object_or_404(
        StaffAttendance,
        restaurant=restaurant,
        staff=staff,
        attendance_date=timezone.localdate(),
        is_deleted=False,
    )

    now = timezone.now()

    attendance.clock_out = now

    if attendance.clock_in:

        worked_minutes = int(
            (
                now - attendance.clock_in
            ).total_seconds() // 60
        )

        attendance.worked_minutes = max(
            worked_minutes - attendance.break_minutes,
            0,
        )

    attendance.save(
        update_fields=[
            "clock_out",
            "worked_minutes",
        ]
    )

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

    return attendance

# ==========================================================
# Get Staff Attendance
# ==========================================================

def get_staff_attendance(
    *,
    restaurant,
    staff_id=None,
    attendance_date=None,
):
    """
    Return attendance records.
    """

    queryset = StaffAttendance.objects.filter(
        restaurant=restaurant,
        is_deleted=False,
    )

    if staff_id:
        queryset = queryset.filter(
            staff_id=staff_id,
        )

    if attendance_date:
        queryset = queryset.filter(
            attendance_date=attendance_date,
        )

    return queryset.order_by(
        "-attendance_date",
        "-created_at",
    )

# ==========================================================
# Update Attendance
# ==========================================================

def update_staff_attendance(
    *,
    restaurant,
    attendance_id,
    **validated_data,
):
    """
    Update attendance record.
    """

    attendance = get_object_or_404(
        StaffAttendance,
        id=attendance_id,
        restaurant=restaurant,
        is_deleted=False,
    )

    for field, value in validated_data.items():
        setattr(
            attendance,
            field,
            value,
        )

    attendance.save()

    return attendance

# ==========================================================
# Attendance Statistics
# ==========================================================

def get_attendance_statistics(
    *,
    restaurant,
):
    """
    Attendance summary.
    """

    queryset = StaffAttendance.objects.filter(
        restaurant=restaurant,
        is_deleted=False,
    )

    return {

        "total_records": queryset.count(),

        "present": queryset.filter(
            status="present",
        ).count(),

        "absent": queryset.filter(
            status="absent",
        ).count(),

        "half_day": queryset.filter(
            status="half_day",
        ).count(),

        "leave": queryset.filter(
            status="leave",
        ).count(),

    }
    
    
