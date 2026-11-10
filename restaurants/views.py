"""Owner restaurant profile, location, delivery zone, hours, settings, branches and tables; public cards and QR codes."""
import base64
import io
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import qrcode
from django.conf import settings
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.geo import valid_point
from common.permissions import IsOwnerOrRole, NotCustomer
from common.tenancy import get_restaurant, is_customer, require_owner, staff_membership, partner_membership

from .models import Branch, Restaurant, Table
from .services import delivery_quote, media_url, normalize_hours, public_card

ZONE_FIELDS = ["enable_delivery", "enable_pickup", "enable_dinein_payment", "catering_available", "max_delivery_km",
               "free_delivery_km", "charge_per_extra_km", "minimum_delivery_order", "average_prep_minutes"]
LOCATION_FIELDS = ["address", "city", "state", "country", "pincode", "phone_country_code"]


def _bool(v):
    return v is True or str(v).strip().lower() in {"true", "1", "yes", "on"}


def _cuisines(raw):
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, str):
        items = raw.split(",")
    else:
        items = []
    out = []
    for c in items:
        name = str(c.get("name", "") if isinstance(c, dict) else c).strip()[:40]
        if name and name.lower() not in [o.lower() for o in out]:
            out.append(name)
    return out[:12]


def _google_url_ok(url):
    try:
        u = urlparse(url)
    except ValueError:
        return False
    host = (u.hostname or "").lower()
    return u.scheme == "https" and (re.search(r"(^|\.)google\.[a-z.]+$", host) is not None or host in {"maps.app.goo.gl", "g.page"})


def profile_data(restaurant, request):
    logo = media_url(request, restaurant.logo)
    cover = media_url(request, restaurant.cover_image)
    from subscriptions.services import active_plan
    plan = active_plan(restaurant)
    return {
        "success": True,
        "restaurant": {
            "id": restaurant.id, "name": restaurant.name, "slug": restaurant.slug, "about": restaurant.about,
            "cuisines": restaurant.cuisines, "cuisine_type": ", ".join(restaurant.cuisines),
            "address": restaurant.address, "phone": restaurant.phone, "email": restaurant.email,
            "google_business_url": restaurant.google_business_url,
            "logo": logo, "logo_url": logo, "cover_image": cover, "cover_image_url": cover,
            "latitude": float(restaurant.latitude) if restaurant.latitude is not None else None,
            "longitude": float(restaurant.longitude) if restaurant.longitude is not None else None,
            "city": restaurant.city, "currency": restaurant.currency, "is_active": restaurant.is_active,
            "created_at": restaurant.created_at,
        },
        "subscription": {"plan": plan.name, "table_limit": plan.table_limit, "menu_item_limit": plan.menu_item_limit},
    }


class ProfileView(APIView):
    permission_classes = [NotCustomer]

    def get(self, request):
        restaurant = get_restaurant(request, required=False)
        if restaurant is None:
            # New owner: the website shows the setup form.
            return Response({"success": True, "restaurant": None, "subscription": None})
        return Response(profile_data(restaurant, request))

    def post(self, request):
        return self._save(request)

    def put(self, request):
        return self._save(request)

    def patch(self, request):
        return self._save(request)

    def _save(self, request):
        if staff_membership(request.user) or partner_membership(request.user):
            raise ValidationError({"detail": "Only the restaurant owner can edit the restaurant profile."})
        d = request.data
        with transaction.atomic():
            restaurant = Restaurant.objects.select_for_update().filter(owner=request.user, deleted_at__isnull=True).first()
            creating = restaurant is None
            r = restaurant or Restaurant(owner=request.user)
            errors = {}
            if "name" in d or creating:
                name = str(d.get("name", "")).strip()
                if not name:
                    errors["name"] = ["Enter your restaurant's name."]
                r.name = name[:150]
            if "phone" in d or creating:
                phone = str(d.get("phone", "")).strip()
                digits = re.sub(r"\D", "", phone)
                if not 10 <= len(digits) <= 15:
                    errors["phone"] = ["Enter a valid phone number (10–15 digits)."]
                r.phone = phone[:20]
            if "email" in d or creating:
                email = str(d.get("email", "")).strip()
                if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
                    errors["email"] = ["Enter a valid email address."]
                r.email = email
            if "google_business_url" in d:
                url = str(d.get("google_business_url") or "").strip()
                if url and not _google_url_ok(url):
                    errors["google_business_url"] = ["Paste a Google Maps link (https://maps.app.goo.gl/… or google.com/maps/…)."]
                r.google_business_url = url
            if "cuisines" in d or "cuisine_type" in d:
                r.cuisines = _cuisines(d.get("cuisines") if "cuisines" in d else d.get("cuisine_type"))
            for field in ("address", "about"):
                if field in d:
                    setattr(r, field, str(d.get(field) or "").strip())
            for field in ("logo", "cover_image"):
                f = request.FILES.get(field)
                if f is not None:
                    if f.size > 10 * 1024 * 1024 or not (f.content_type or "").startswith("image/"):
                        errors[field] = ["Upload an image under 10 MB."]
                    else:
                        setattr(r, field, f)
                elif field in d and d.get(field) in ("", None, "null"):
                    setattr(r, field, None)
            if errors:
                raise ValidationError(errors)
            r.save()
            from subscriptions.services import ensure_subscription
            ensure_subscription(r)
        return Response(profile_data(r, request), status=201 if creating else 200)


def _owner_restaurant(request):
    return get_restaurant(request, allow_staff=True)


class LocationView(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ["manager"]

    def get(self, request):
        r = get_restaurant(request, required=False)
        if r is None:
            return Response({"latitude": None, "longitude": None, "address": ""})
        return Response(self._out(r))

    def put(self, request):
        r = _owner_restaurant(request)
        d = request.data
        if not valid_point(d.get("latitude"), d.get("longitude")):
            raise ValidationError({"latitude": ["Pick a valid location on the map."]})
        r.latitude = Decimal(str(round(float(d["latitude"]), 6)))
        r.longitude = Decimal(str(round(float(d["longitude"]), 6)))
        for f in LOCATION_FIELDS:
            if f in d:
                setattr(r, f, str(d.get(f) or "").strip())
        r.save()
        return Response(self._out(r))

    patch = put
    post = put

    @staticmethod
    def _out(r):
        return {"latitude": float(r.latitude) if r.latitude is not None else None,
                "longitude": float(r.longitude) if r.longitude is not None else None,
                **{f: getattr(r, f) for f in LOCATION_FIELDS}}


class ZoneView(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ["manager"]

    def get(self, request):
        r = get_restaurant(request, required=False)
        if r is None:
            return Response({f: Restaurant._meta.get_field(f).default for f in ZONE_FIELDS})
        return Response(self._out(r))

    def put(self, request):
        r = _owner_restaurant(request)
        d = request.data
        errors = {}
        for f in ZONE_FIELDS:
            if f not in d:
                continue
            if f.startswith("enable_") or f == "catering_available":
                setattr(r, f, _bool(d[f]))
                continue
            try:
                value = Decimal(str(d[f] if d[f] not in (None, "") else 0))
            except InvalidOperation:
                errors[f] = ["Enter a number."]
                continue
            if value < 0:
                errors[f] = ["Can't be negative."]
                continue
            setattr(r, f, int(value) if f == "average_prep_minutes" else value)
        if r.free_delivery_km > r.max_delivery_km:
            errors["free_delivery_km"] = ["Free delivery distance can't be more than the delivery radius."]
        if errors:
            raise ValidationError(errors)
        r.save()
        return Response(self._out(r))

    patch = put

    @staticmethod
    def _out(r):
        out = {}
        for f in ZONE_FIELDS:
            v = getattr(r, f)
            out[f] = float(v) if isinstance(v, Decimal) else v
        return out


class HoursView(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ["manager"]

    def get(self, request):
        r = get_restaurant(request, required=False)
        from .models import default_hours
        return Response(r.working_hours if r else default_hours())

    def put(self, request):
        r = _owner_restaurant(request)
        r.working_hours = normalize_hours(request.data)
        r.save(update_fields=["working_hours", "updated_at"])
        return Response(r.working_hours)

    patch = put
    post = put


class SettingsView(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ["manager"]

    def get(self, request):
        r = get_restaurant(request, required=False)
        return Response(r.settings if r else {})

    def put(self, request):
        r = _owner_restaurant(request)
        if not isinstance(request.data, dict):
            raise ValidationError({"detail": "Send settings as an object."})
        r.settings = {**(r.settings or {}), **{k: v for k, v in request.data.items()}}
        r.save(update_fields=["settings", "updated_at"])
        return Response(r.settings)

    patch = put


# ─── Branches ─────────────────────────────────────────────────────────────

def branch_out(b):
    out = {"id": b.id, "name": b.name, "city": b.city, "address": b.address, "phone": b.phone, "is_active": b.is_active,
           "is_main": b.is_main, "created_at": b.created_at, "tables": b.tables.count(),
           "latitude": float(b.latitude) if b.latitude is not None else None,
           "longitude": float(b.longitude) if b.longitude is not None else None}
    from django.apps import apps
    if apps.is_installed("payments"):
        from payments.routing import routes_to
        out["payment"] = routes_to(b)
    return out


class BranchList(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ["manager"]

    def get(self, request):
        r = get_restaurant(request, required=False)
        if r is None:
            return Response([])
        r.main_branch()
        return Response([branch_out(b) for b in r.branches.all()])

    def post(self, request):
        r = require_owner(request)
        b = Branch(restaurant=r)
        _apply_branch(b, request.data, creating=True)
        try:
            with transaction.atomic():
                b.save()
        except IntegrityError:
            raise ValidationError({"name": ["A branch with this name already exists."]})
        from django.apps import apps
        if apps.is_installed("inventory"):
            from inventory.services import init_branch_stock
            init_branch_stock(b)
        return Response(branch_out(b), status=201)


def _apply_branch(b, d, creating=False):
    if "name" in d or creating:
        name = str(d.get("name", "")).strip()
        if not name:
            raise ValidationError({"name": ["Branch name is required."]})
        if Branch.objects.filter(restaurant=b.restaurant, name__iexact=name).exclude(pk=b.pk).exists():
            raise ValidationError({"name": ["A branch with this name already exists."]})
        b.name = name[:120]
    for f in ("city", "address", "phone"):
        if f in d:
            setattr(b, f, str(d.get(f) or "").strip())
    if "latitude" in d or "longitude" in d:
        if d.get("latitude") in (None, "") and d.get("longitude") in (None, ""):
            b.latitude = b.longitude = None
        elif valid_point(d.get("latitude"), d.get("longitude")):
            b.latitude, b.longitude = Decimal(str(round(float(d["latitude"]), 6))), Decimal(str(round(float(d["longitude"]), 6)))
        else:
            raise ValidationError({"latitude": ["Pick a valid location."]})
    if "is_active" in d:
        active = _bool(d["is_active"])
        if not active and b.is_main:
            raise ValidationError({"detail": "The main branch can't be switched off."})
        b.is_active = active


class BranchDetail(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ["manager"]

    def get(self, request, pk):
        r = get_restaurant(request)
        return Response(branch_out(get_object_or_404(Branch, pk=pk, restaurant=r)))

    def patch(self, request, pk):
        r = require_owner(request)
        with transaction.atomic():
            b = get_object_or_404(Branch.objects.select_for_update(), pk=pk, restaurant=r)
            _apply_branch(b, request.data)
            if _bool(request.data.get("is_main", False)) and not b.is_main:
                Branch.objects.filter(restaurant=r, is_main=True).update(is_main=False)
                b.is_main, b.is_active = True, True
            b.save()
        return Response(branch_out(b))

    put = patch

    def delete(self, request, pk):
        r = require_owner(request)
        b = Branch.objects.filter(pk=pk, restaurant=r).first()
        if b is None:
            return Response(status=204)
        if b.is_main:
            raise ValidationError({"detail": "The main branch can't be deleted."})
        from django.apps import apps
        if apps.is_installed("orders"):
            from orders.models import Order
            if Order.objects.filter(branch=b).exclude(status__in=["completed", "cancelled"]).exists():
                raise ValidationError({"detail": "This branch has open orders. Finish or cancel them first."})
        if b.tables.exists():
            raise ValidationError({"detail": "Move or delete this branch's tables first."})
        b.delete()
        return Response(status=204)


# ─── Tables ───────────────────────────────────────────────────────────────

def table_out(t):
    return {"id": t.id, "table_number": t.table_number, "branch_id": t.branch_id, "branch": t.branch_id,
            "branch_name": t.branch.name, "qr_url": f"{settings.FRONTEND_URL}/menu/{t.id}", "created_at": t.created_at}


class TableList(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ["manager", "waiter", "cashier"]

    def get(self, request):
        r = get_restaurant(request, required=False)
        if r is None:
            return Response([])
        qs = r.tables.select_related("branch")
        branch = request.query_params.get("branch")
        member = staff_membership(request.user)
        if member and member.branch_id:
            qs = qs.filter(branch_id=member.branch_id)
        elif branch not in (None, "", "all"):
            qs = qs.filter(branch_id=branch)
        return Response([table_out(t) for t in qs])

    def post(self, request):
        r = get_restaurant(request)
        number = str(request.data.get("table_number", "")).strip()[:20]
        if not number:
            raise ValidationError({"table_number": ["Enter a table number."]})
        from common.tenancy import get_branch
        branch = get_branch(request, r)
        with transaction.atomic():
            Restaurant.objects.select_for_update().get(pk=r.pk)
            from subscriptions.services import check_limit
            check_limit(r, "tables")
            if r.tables.filter(table_number__iexact=number).exists():
                raise ValidationError({"table_number": ["A table with this number already exists."]})
            t = Table.objects.create(restaurant=r, branch=branch, table_number=number)
        return Response(table_out(t), status=201)


class TableDetail(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ["manager"]

    def get(self, request, pk):
        r = get_restaurant(request)
        return Response(table_out(get_object_or_404(Table.objects.select_related("branch"), pk=pk, restaurant=r)))

    def delete(self, request, pk):
        r = get_restaurant(request)
        t = get_object_or_404(Table, pk=pk, restaurant=r)
        t.delete()
        return Response(status=204)


# ─── QR codes ─────────────────────────────────────────────────────────────

def _qr(url):
    img = qrcode.make(url, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return {"url": url, "image": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}


@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def qr_table(request, pk):
    r = get_restaurant(request)
    t = get_object_or_404(Table, pk=pk, restaurant=r)
    return Response(_qr(f"{settings.FRONTEND_URL}/menu/{t.id}"))


@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def qr_pickup(request):
    r = get_restaurant(request)
    return Response(_qr(f"{settings.FRONTEND_URL}/pickup?restaurant={r.id}"))


@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def qr_delivery(request):
    r = get_restaurant(request)
    return Response(_qr(f"{settings.FRONTEND_URL}/delivery?restaurant={r.id}"))


# ─── Public ───────────────────────────────────────────────────────────────

def _public_qs():
    return Restaurant.objects.filter(is_active=True, deleted_at__isnull=True)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def public_restaurant(request, pk):
    r = get_object_or_404(_public_qs(), pk=pk)
    return Response(public_card(r, request, request.query_params.get("lat"), request.query_params.get("lng")))


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def nearby(request):
    """Restaurants within `radius` km (default 10) of a point, nearest first. Only restaurants diners can order from."""
    q = request.query_params
    lat, lng = q.get("lat", q.get("latitude")), q.get("lng", q.get("longitude"))
    if not valid_point(lat, lng):
        raise ValidationError({"lat": ["Send a valid lat and lng."]})
    try:
        radius = min(max(float(q.get("radius", 10)), 0.5), 50)
    except ValueError:
        radius = 10
    lat_f, lng_f = float(lat), float(lng)
    span = radius / 111.0 + 0.01
    qs = _public_qs().filter(latitude__isnull=False, longitude__isnull=False, tables__isnull=False,
                             latitude__range=(lat_f - span, lat_f + span)).distinct()
    cuisine = (q.get("cuisine") or "").strip().lower()
    rows = []
    for r in qs:
        card = public_card(r, request, lat_f, lng_f)
        if card["distance_km"] > radius:
            continue
        if cuisine and cuisine not in [c.lower() for c in r.cuisines]:
            continue
        rows.append(card)
    rows.sort(key=lambda c: c["distance_km"])
    return Response(rows[:100])


@api_view(["GET", "POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def quote(request):
    d = request.data if request.method == "POST" else request.query_params
    r = get_object_or_404(_public_qs(), pk=d.get("restaurant_id") or d.get("restaurant") or 0)
    return Response(delivery_quote(r, d.get("latitude", d.get("lat")), d.get("longitude", d.get("lng")), d.get("subtotal") or 0))
