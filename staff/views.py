"""Staff list and profiles, shift clock-in/out and breaks, and "who am I" for staff screens."""
import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.invites import login_for, set_active
from common.permissions import IsOwnerOrRole
from common.photos import take_photo
from common.tenancy import get_restaurant, is_customer, owned_restaurant, partner_membership, staff_membership
from restaurants.models import Branch
from restaurants.services import media_url

from .models import ROLES, Attendance, StaffBreak, StaffMember

READ_ROLES = ["manager"]


def _with_roles(view, roles):
    view.cls.allowed_roles = roles
    return view


def staff_out(s, request):
    photo = media_url(request, s.profile_photo)
    return {"id": s.id, "first_name": s.first_name, "last_name": s.last_name, "full_name": s.full_name, "name": s.full_name,
            "employee_id": s.employee_id, "phone": s.phone, "country_code": s.country_code, "email": s.email,
            "designation": s.designation, "role": s.role, "is_active": s.is_active, "shift_status": s.shift_status,
            "staff_status": s.shift_status, "branch": s.branch_id, "branch_name": s.branch.name if s.branch else None,
            "has_login": bool(s.user_id), "profile_photo": photo, "photo": photo, "shift_schedule": s.shift_schedule,
            "last_active_at": s.last_active_at, "last_login_at": s.user.last_login if s.user else None, "created_at": s.created_at}


def _owner_only(request):
    """Adding, editing and removing staff is for the owner (or a co-owner)."""
    member = staff_membership(request.user)
    if member is not None and member.role != "owner":
        raise PermissionDenied("Only the owner can change staff.")
    return get_restaurant(request)


def _apply(s, request, creating):
    d = request.data
    errors = {}

    def text(k, n):
        return str(d.get(k) or "").strip()[:n]

    if "first_name" in d or creating:
        s.first_name = text("first_name", 60)
        if len(s.first_name) < 2:
            errors["first_name"] = ["Enter at least 2 letters."]
    if "last_name" in d:
        s.last_name = text("last_name", 60)
    if "employee_id" in d or creating:
        s.employee_id = text("employee_id", 30).upper()
        if len(s.employee_id) < 2:
            errors["employee_id"] = ["Enter an employee ID (at least 2 characters)."]
        elif StaffMember.objects.filter(restaurant=s.restaurant, employee_id=s.employee_id).exclude(pk=s.pk).exists():
            errors["employee_id"] = ["Another staff member has this employee ID."]
    if "phone" in d:
        s.phone = text("phone", 20)
        if s.phone and len(re.sub(r"\D", "", s.phone)) < 8:
            errors["phone"] = ["Enter a valid phone number."]
    if "country_code" in d:
        s.country_code = text("country_code", 6) or "+91"
    if "designation" in d:
        s.designation = text("designation", 80)
    if "role" in d or creating:
        role = text("role", 20).lower() or "cashier"
        if role not in ROLES:
            errors["role"] = ["Pick a role from the list."]
        s.role = role
    if "is_active" in d:
        s.is_active = str(d.get("is_active")).lower() in {"true", "1", "on", "yes"}
    if "branch" in d:
        raw = d.get("branch")
        if raw in (None, "", "null"):
            s.branch = None
        else:
            s.branch = Branch.objects.filter(restaurant=s.restaurant, pk=raw).first()
            if s.branch is None:
                errors["branch"] = ["Branch not found."]
    email = text("email", 254).lower() if "email" in d else None
    if email:
        try:
            validate_email(email)
        except DjangoValidationError:
            errors["email"] = ["Enter a valid email."]
    if errors:
        raise ValidationError(errors)
    take_photo(request, s)
    return email


def _save(s, request, creating):
    email = _apply(s, request, creating)
    with transaction.atomic():
        if email is not None:
            s.email = email
            if email:
                s.user = login_for(email, s.first_name, s.last_name, s.restaurant, f"{s.role.replace('_', ' ')}", s.user)
        try:
            s.save()
        except IntegrityError:
            raise ValidationError({"employee_id": ["Another staff member has this employee ID."]})
        set_active(s.user, s.is_active)
    return s


@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def staff_list(request):
    r = get_restaurant(request, required=False)
    if r is None:
        return Response([])
    qs = StaffMember.objects.filter(restaurant=r).select_related("branch", "user")
    return Response([staff_out(s, request) for s in qs])


_with_roles(staff_list, READ_ROLES)


@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def staff_create(request):
    r = _owner_only(request)
    s = _save(StaffMember(restaurant=r), request, True)
    return Response(staff_out(s, request), status=201)


def _member(request, pk):
    r = get_restaurant(request)
    return get_object_or_404(StaffMember.objects.select_related("branch", "user"), pk=pk, restaurant=r)


@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def staff_detail(request, pk):
    return Response(staff_out(_member(request, pk), request))


_with_roles(staff_detail, READ_ROLES)


@api_view(["PATCH", "PUT"])
@permission_classes([IsOwnerOrRole])
def staff_update(request, pk):
    _owner_only(request)
    s = _member(request, pk)
    if s.user_id == request.user.id and "role" in request.data and request.data.get("role") != s.role:
        raise ValidationError({"role": ["You can't change your own role."]})
    return Response(staff_out(_save(s, request, False), request))


@api_view(["DELETE"])
@permission_classes([IsOwnerOrRole])
def staff_delete(request, pk):
    _owner_only(request)
    s = _member(request, pk)
    if s.user_id == request.user.id:
        raise ValidationError({"detail": "You can't remove yourself."})
    set_active(s.user, False)
    if s.profile_photo:
        s.profile_photo.delete(save=False)
    s.delete()
    return Response(status=204)


@api_view(["GET", "PATCH"])
@permission_classes([IsOwnerOrRole])
def staff_role(request, pk):
    s = _member(request, pk)
    if request.method == "GET":
        return Response({"id": s.id, "role": s.role, "roles": ROLES})
    _owner_only(request)
    role = str(request.data.get("role") or "").lower()
    if role not in ROLES:
        raise ValidationError({"role": ["Pick a role from the list."]})
    if s.user_id == request.user.id:
        raise ValidationError({"role": ["You can't change your own role."]})
    s.role = role
    s.save(update_fields=["role"])
    return Response(staff_out(s, request))


_with_roles(staff_role, READ_ROLES)


@api_view(["PATCH", "PUT"])
@permission_classes([IsOwnerOrRole])
def staff_schedule(request, pk):
    s = _member(request, pk)
    if not isinstance(request.data, dict):
        raise ValidationError({"detail": "Send the schedule as an object."})
    s.shift_schedule = dict(request.data)
    s.save(update_fields=["shift_schedule"])
    return Response(staff_out(s, request))


_with_roles(staff_schedule, READ_ROLES)


# ─── Shifts and breaks ───────────────────────────────────────────────────

def _open_attendance(s):
    return s.attendance.filter(clock_out__isnull=True).order_by("-clock_in").first()


def _open_break(s):
    return s.breaks.filter(break_end__isnull=True).order_by("-break_start").first()


@transaction.atomic
def shift_action(s, action):
    s = StaffMember.objects.select_for_update().get(pk=s.pk)
    now = timezone.now()
    att, brk = _open_attendance(s), _open_break(s)
    if action == "clock_in":
        if brk:  # "on shift" while on a break means the break is over
            brk.break_end = now
            brk.save(update_fields=["break_end"])
        elif att:
            raise ValidationError({"detail": f"{s.first_name} is already clocked in."})
        if not att:
            Attendance.objects.create(staff=s, attendance_date=timezone.localdate(now), clock_in=now)
        s.shift_status = StaffMember.Shift.ON
    elif action == "clock_out":
        if not att:
            raise ValidationError({"detail": f"{s.first_name} isn't clocked in."})
        if brk:
            brk.break_end = now
            brk.save(update_fields=["break_end"])
        att.clock_out = now
        att.save(update_fields=["clock_out"])
        s.shift_status = StaffMember.Shift.OFF
    elif action == "start_break":
        if not att:
            raise ValidationError({"detail": f"Clock {s.first_name} in before starting a break."})
        if brk:
            raise ValidationError({"detail": f"{s.first_name} is already on a break."})
        StaffBreak.objects.create(staff=s, break_start=now)
        s.shift_status = StaffMember.Shift.BREAK
    elif action == "end_break":
        if not brk:
            raise ValidationError({"detail": f"{s.first_name} isn't on a break."})
        brk.break_end = now
        brk.save(update_fields=["break_end"])
        s.shift_status = StaffMember.Shift.ON
    else:
        raise ValidationError({"action": ["Pick clock in, clock out, start break or end break."]})
    s.last_active_at = now
    s.save(update_fields=["shift_status", "last_active_at"])
    return s


@api_view(["PATCH", "POST"])
@permission_classes([IsOwnerOrRole])
def staff_shift(request, pk):
    s = shift_action(_member(request, pk), str(request.data.get("action") or ""))
    return Response(staff_out(StaffMember.objects.select_related("branch", "user").get(pk=s.pk), request))


_with_roles(staff_shift, READ_ROLES)


def attendance_out(a):
    end = a.clock_out
    hours = round(((end or timezone.now()) - a.clock_in).total_seconds() / 3600, 2)
    return {"id": a.id, "staff": a.staff_id, "staff_name": a.staff.full_name, "attendance_date": a.attendance_date,
            "clock_in": a.clock_in, "clock_out": a.clock_out, "total_hours": hours if end else None,
            "status": "completed" if end else "on_shift", "note": a.note}


def break_out(b):
    mins = round((b.break_end - b.break_start).total_seconds() / 60) if b.break_end else None
    return {"id": b.id, "staff": b.staff_id, "staff_name": b.staff.full_name, "break_start": b.break_start,
            "break_end": b.break_end, "duration_minutes": mins}


def _staff_for_action(request):
    r = get_restaurant(request)
    raw = request.data.get("staff_id") or request.data.get("staff")
    if raw in (None, ""):
        member = staff_membership(request.user)
        if member is None:
            raise ValidationError({"staff_id": ["Pick a staff member."]})
        return member
    return get_object_or_404(StaffMember, pk=raw, restaurant=r)


@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def attendance_list(request):
    r = get_restaurant(request, required=False)
    if r is None:
        return Response([])
    qs = Attendance.objects.filter(staff__restaurant=r).select_related("staff")
    q = request.query_params
    if q.get("staff_id"):
        qs = qs.filter(staff_id=q.get("staff_id"))
    if q.get("attendance_date"):
        qs = qs.filter(attendance_date=q.get("attendance_date"))
    return Response([attendance_out(a) for a in qs[:500]])


_with_roles(attendance_list, READ_ROLES)


def _act(action):
    @api_view(["POST"])
    @permission_classes([IsOwnerOrRole])
    def view(request):
        s = shift_action(_staff_for_action(request), action)
        if action in ("clock_in", "clock_out"):
            a = s.attendance.order_by("-clock_in").first()
            return Response(attendance_out(a))
        b = s.breaks.order_by("-break_start").first()
        return Response(break_out(b))
    return _with_roles(view, READ_ROLES)


clock_in, clock_out, break_start, break_end = (_act(a) for a in ("clock_in", "clock_out", "start_break", "end_break"))


@api_view(["PATCH"])
@permission_classes([IsOwnerOrRole])
def attendance_edit(request, pk):
    """Owner corrections to a shift's times."""
    _owner_only(request)
    from django.utils.dateparse import parse_datetime
    a = get_object_or_404(Attendance.objects.select_related("staff"), pk=pk, staff__restaurant=get_restaurant(request))
    for f in ("clock_in", "clock_out"):
        if f in request.data:
            v = request.data.get(f)
            dt = parse_datetime(str(v)) if v not in (None, "") else None
            if v not in (None, "") and dt is None:
                raise ValidationError({f: ["Enter a valid date and time."]})
            if f == "clock_in" and dt is None:
                raise ValidationError({f: ["A shift needs a start time."]})
            setattr(a, f, dt)
    if a.clock_out and a.clock_out <= a.clock_in:
        raise ValidationError({"clock_out": ["Clock-out must be after clock-in."]})
    if "note" in request.data:
        a.note = str(request.data.get("note") or "")[:255]
    a.attendance_date = timezone.localdate(a.clock_in)
    a.save()
    return Response(attendance_out(a))


@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def breaks_list(request):
    r = get_restaurant(request, required=False)
    if r is None:
        return Response([])
    qs = StaffBreak.objects.filter(staff__restaurant=r).select_related("staff")
    if request.query_params.get("staff_id"):
        qs = qs.filter(staff_id=request.query_params.get("staff_id"))
    return Response([break_out(b) for b in qs[:500]])


_with_roles(breaks_list, READ_ROLES)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """Who is signed in, for the staff home screen: owner, staff role, or delivery partner."""
    u = request.user
    if is_customer(u):
        raise PermissionDenied("Diner accounts don't have staff tools.")
    r = owned_restaurant(u)
    if r is not None:
        return Response({"id": u.id, "name": u.get_full_name() or u.username, "role": "owner", "restaurant_id": r.id, "branch_id": None})
    m = staff_membership(u)
    if m is not None:
        return Response({"id": m.id, "name": m.full_name, "role": m.role, "restaurant_id": m.restaurant_id, "branch_id": m.branch_id})
    p = partner_membership(u)
    if p is not None:
        return Response({"id": p.id, "name": p.full_name, "role": "delivery", "restaurant_id": p.restaurant_id, "branch_id": None})
    raise PermissionDenied("This account isn't linked to a restaurant.")
