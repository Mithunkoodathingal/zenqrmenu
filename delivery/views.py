"""Restaurant side: riders and assigning them to delivery orders. Rider side: my trips, start, delivered, location."""
import re
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.invites import login_for, set_active
from common.geo import valid_point
from common.permissions import IsOwnerOrRole
from common.photos import take_photo
from common.tenancy import get_restaurant, partner_membership
from orders.models import Order, OrderEvent
from orders.serializers import order_out
from orders.services import set_status

from .models import VEHICLES, DeliveryAssignment, DeliveryPartner
from .services import ACTIVE, active_assignment, end_assignment, photo_url

ROLES = ["manager", "delivery_manager"]


class IsPartner(BasePermission):
    message = "Only delivery partners can do this."

    def has_permission(self, request, view):
        return partner_membership(request.user) is not None


def partner_out(p):
    active = list(Order.objects.filter(delivery_assignments__partner=p, delivery_assignments__status__in=ACTIVE)
                  .values_list("order_number", flat=True))
    photo = photo_url(p.profile_photo)
    return {"id": p.id, "first_name": p.first_name, "last_name": p.last_name, "full_name": p.full_name, "phone": p.phone,
            "email": p.email, "vehicle_type": p.vehicle_type, "vehicle_number": p.vehicle_number, "is_active": p.is_active,
            "is_available": p.is_available, "latitude": float(p.latitude) if p.latitude is not None else None,
            "longitude": float(p.longitude) if p.longitude is not None else None,
            "last_location_update": p.last_location_update, "profile_photo": photo, "photo": photo,
            "active_orders": active, "has_login": bool(p.user_id), "created_at": p.created_at}


def _apply(p, request, creating):
    d = request.data
    errors = {}

    def text(k, n):
        return str(d.get(k) or "").strip()[:n]

    if "first_name" in d or creating:
        p.first_name = text("first_name", 60)
        if not p.first_name:
            errors["first_name"] = ["Enter the rider's first name."]
    if "last_name" in d:
        p.last_name = text("last_name", 60)
    if "phone" in d or creating:
        p.phone = text("phone", 20)
        if len(re.sub(r"\D", "", p.phone)) < 8:
            errors["phone"] = ["Enter a valid phone number."]
        elif DeliveryPartner.objects.filter(restaurant=p.restaurant, phone=p.phone).exclude(pk=p.pk).exists():
            errors["phone"] = ["Another rider has this phone number."]
    if "vehicle_type" in d:
        v = text("vehicle_type", 10).lower()
        if v and v not in VEHICLES:
            errors["vehicle_type"] = ["Pick bike, scooter, cycle or car."]
        p.vehicle_type = v
    if "vehicle_number" in d:
        p.vehicle_number = text("vehicle_number", 20).upper()
    if "is_active" in d:
        p.is_active = str(d.get("is_active")).lower() in {"true", "1", "on", "yes"}
    email = text("email", 254).lower() if "email" in d else None
    if email:
        try:
            validate_email(email)
        except DjangoValidationError:
            errors["email"] = ["Enter a valid email."]
    if errors:
        raise ValidationError(errors)
    take_photo(request, p)
    with transaction.atomic():
        if email is not None:
            p.email = email
            if email:
                p.user = login_for(email, p.first_name, p.last_name, p.restaurant, "a delivery partner", p.user)
        try:
            p.save()
        except IntegrityError:
            raise ValidationError({"phone": ["Another rider has this phone number."]})
        set_active(p.user, p.is_active)
    return p


class PartnerList(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ROLES

    def get(self, request):
        r = get_restaurant(request, required=False)
        rows = [partner_out(p) for p in DeliveryPartner.objects.filter(restaurant=r)] if r else []
        return Response({"success": True, "delivery_partners": rows})

    def post(self, request):
        p = _apply(DeliveryPartner(restaurant=get_restaurant(request)), request, True)
        return Response({"success": True, "delivery_partner": partner_out(p)}, status=201)


class PartnerDetail(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ROLES

    def _get(self, request, pk):
        return get_object_or_404(DeliveryPartner, pk=pk, restaurant=get_restaurant(request))

    def get(self, request, pk):
        return Response({"success": True, "delivery_partner": partner_out(self._get(request, pk))})

    def patch(self, request, pk):
        return Response({"success": True, "delivery_partner": partner_out(_apply(self._get(request, pk), request, False))})

    put = patch

    def delete(self, request, pk):
        p = self._get(request, pk)
        if p.assignments.filter(status__in=ACTIVE).exists():
            raise ValidationError({"detail": f"{p.first_name} is carrying an order. Unassign or finish it first."})
        set_active(p.user, False)
        if p.profile_photo:
            p.profile_photo.delete(save=False)
        p.delete()
        return Response(status=204)


def _with_roles(view, roles):
    view.cls.allowed_roles = roles
    return view


@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def availability(request, pk):
    p = get_object_or_404(DeliveryPartner, pk=pk, restaurant=get_restaurant(request))
    want = str(request.data.get("is_available")).lower() in {"true", "1", "on", "yes"}
    if want and not p.is_active:
        raise ValidationError({"detail": f"{p.first_name} is deactivated."})
    p.is_available = want
    p.save(update_fields=["is_available"])
    return Response({"success": True, "delivery_partner": partner_out(p)})


_with_roles(availability, ROLES)


def _point(d):
    lat, lng = d.get("latitude"), d.get("longitude")
    if not valid_point(lat, lng):
        raise ValidationError({"detail": "Send a valid latitude and longitude."})
    return Decimal(str(round(float(lat), 6))), Decimal(str(round(float(lng), 6)))


def _save_location(p, d):
    p.latitude, p.longitude = _point(d)
    acc = d.get("accuracy")
    try:
        p.location_accuracy_m = float(acc) if acc not in (None, "") else None
    except (TypeError, ValueError):
        p.location_accuracy_m = None
    p.last_location_update = timezone.now()
    p.save(update_fields=["latitude", "longitude", "location_accuracy_m", "last_location_update"])


@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def owner_location(request, pk):
    p = get_object_or_404(DeliveryPartner, pk=pk, restaurant=get_restaurant(request))
    _save_location(p, request.data)
    return Response({"success": True})


_with_roles(owner_location, ROLES)


@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def assign(request, pk):
    r = get_restaurant(request)
    with transaction.atomic():
        o = get_object_or_404(Order.objects.select_for_update(), pk=pk, restaurant=r, deleted_at__isnull=True)
        if o.order_type != Order.Type.DELIVERY:
            raise ValidationError({"detail": "Only delivery orders get a rider."})
        if not o.is_open:
            raise ValidationError({"detail": "This order is already finished."})
        if active_assignment(o) is not None:
            raise ValidationError({"detail": "This order already has a rider. Unassign them first."})
        raw = request.data.get("delivery_partner") or request.data.get("partner_id")
        p = DeliveryPartner.objects.select_for_update().filter(pk=raw, restaurant=r).first() if raw not in (None, "") else None
        if p is None:
            raise ValidationError({"delivery_partner": ["Pick a rider."]})
        if not p.is_active or not p.is_available:
            raise ValidationError({"detail": f"{p.first_name} isn't available right now."})
        DeliveryAssignment.objects.create(order=o, partner=p)
        p.is_available = False
        p.save(update_fields=["is_available"])
        OrderEvent.objects.create(order=o, status="rider_assigned", note=p.full_name[:255])
    return Response({"success": True, "order": order_out(Order.objects.get(pk=o.pk))})


_with_roles(assign, ROLES)


@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def unassign(request, pk):
    o = get_object_or_404(Order, pk=pk, restaurant=get_restaurant(request), deleted_at__isnull=True)
    a = active_assignment(o)
    if a is not None:
        end_assignment(a, DeliveryAssignment.Status.CANCELLED)
    return Response({"success": True, "order": order_out(Order.objects.get(pk=o.pk))})


_with_roles(unassign, ROLES)


# ─── Rider's own screens ─────────────────────────────────────────────────

def trip_out(a):
    o = a.order
    return {"id": a.id, "order_id": o.id, "order_number": o.order_number, "customer_name": o.customer_name,
            "customer_phone": o.customer_phone, "address": o.customer_address, "status": a.status,
            "order_status": o.status, "total_price": float(o.total), "payment_method": o.payment_method,
            "payment_status": o.payment_status, "customer_note": o.customer_note,
            "delivery_latitude": float(o.delivery_latitude) if o.delivery_latitude is not None else None,
            "delivery_longitude": float(o.delivery_longitude) if o.delivery_longitude is not None else None,
            "assigned_at": a.assigned_at, "started_at": a.started_at}


@api_view(["GET"])
@permission_classes([IsPartner])
def my_assignments(request):
    p = partner_membership(request.user)
    since = timezone.now() - timezone.timedelta(hours=12)
    qs = (DeliveryAssignment.objects.filter(partner=p).filter(status__in=ACTIVE) |
          DeliveryAssignment.objects.filter(partner=p, ended_at__gte=since)).select_related("order").order_by("-assigned_at")
    return Response([trip_out(a) for a in qs[:50]])


def _my_trip(request, pk):
    return get_object_or_404(DeliveryAssignment.objects.select_related("order", "partner"), pk=pk,
                             partner=partner_membership(request.user))


@api_view(["POST"])
@permission_classes([IsPartner])
def start_trip(request, pk):
    a = _my_trip(request, pk)
    if a.status == DeliveryAssignment.Status.STARTED:
        return Response(trip_out(a))
    if a.status != DeliveryAssignment.Status.ASSIGNED:
        raise ValidationError({"detail": "This trip is no longer yours."})
    if a.order.status != Order.Status.READY:
        raise ValidationError({"detail": "The kitchen hasn't marked this order ready yet."})
    a.status, a.started_at = DeliveryAssignment.Status.STARTED, timezone.now()
    a.save(update_fields=["status", "started_at"])
    OrderEvent.objects.create(order=a.order, status="out_for_delivery")
    return Response(trip_out(a))


@api_view(["POST"])
@permission_classes([IsPartner])
def delivered(request, pk):
    a = _my_trip(request, pk)
    if a.status == DeliveryAssignment.Status.DELIVERED:
        return Response(trip_out(a))
    if a.status != DeliveryAssignment.Status.STARTED:
        raise ValidationError({"detail": "Start the trip before marking it delivered."})
    code = request.data.get("otp") or request.data.get("code")
    if code:
        from orders.services import verify_handover_code
        verify_handover_code(a.order, code)
    set_status(a.order, Order.Status.COMPLETED, f"Delivered by {a.partner.full_name}")  # also ends the trip
    a.refresh_from_db()
    return Response(trip_out(a))


@api_view(["POST"])
@permission_classes([IsPartner])
def trip_location(request, pk):
    a = _my_trip(request, pk)
    if a.status not in ACTIVE:
        raise ValidationError({"detail": "This trip has ended."})
    _save_location(a.partner, request.data)
    return Response({"success": True})


@api_view(["POST"])
@permission_classes([IsPartner])
def my_availability(request):
    p = partner_membership(request.user)
    p.is_available = str(request.data.get("is_available")).lower() in {"true", "1", "on", "yes"}
    p.save(update_fields=["is_available"])
    return Response({"success": True, "is_available": p.is_available})

