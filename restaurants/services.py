"""Opening hours, delivery charges and the public restaurant card shared by discovery, menus and checkout."""
import re
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from common.geo import haversine_km, money, valid_point

from .models import DAYS

SHORT = {"mon": "monday", "tue": "tuesday", "wed": "wednesday", "thu": "thursday", "fri": "friday", "sat": "saturday", "sun": "sunday"}
HHMM = re.compile(r"^([01]?\d|2[0-3]):[0-5]\d")


def normalize_hours(raw):
    """Accept the server shape (monday/is_open/open/close) or the website's short shape; return the server shape."""
    if not isinstance(raw, dict):
        raise ValidationError({"working_hours": ["Send a weekly schedule."]})
    src = raw.get("working_hours") if isinstance(raw.get("working_hours"), dict) else raw
    out = {}
    for short, day in SHORT.items():
        d = src.get(day, src.get(short)) or {}
        if not isinstance(d, dict):
            raise ValidationError({day: ["Invalid day schedule."]})
        is_open = d.get("is_open", d.get("open") if isinstance(d.get("open"), bool) else True)
        opens = d.get("open") if isinstance(d.get("open"), str) else d.get("opens", "09:00")
        closes = d.get("close", d.get("closes", "22:00"))
        if not (isinstance(opens, str) and HHMM.match(opens) and isinstance(closes, str) and HHMM.match(closes)):
            raise ValidationError({day: ["Times must look like 09:00."]})
        if bool(is_open) and opens[:5] >= closes[:5] and closes[:5] != "00:00":
            raise ValidationError({day: ["Closing time must be after opening time."]})
        out[day] = {"is_open": bool(is_open), "open": opens[:5], "close": closes[:5]}
    holidays = src.get("holidays") or []
    if not isinstance(holidays, list) or not all(isinstance(h, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", h) for h in holidays):
        raise ValidationError({"holidays": ["Holidays must be dates like 2026-12-25."]})
    out["holidays"] = sorted(set(holidays))
    if isinstance(src.get("timezone"), str):
        out["timezone"] = src["timezone"]
    return out


def _tz(restaurant):
    try:
        return ZoneInfo((restaurant.working_hours or {}).get("timezone") or settings.TIME_ZONE)
    except Exception:
        return ZoneInfo(settings.TIME_ZONE)


def _minutes(hhmm):
    h, m = hhmm[:5].split(":")
    return int(h) * 60 + int(m)


def is_open_at(restaurant, when=None):
    """True when the restaurant takes orders at `when` (default now), using its own time zone."""
    hours = restaurant.working_hours or {}
    local = (when or timezone.now()).astimezone(_tz(restaurant))
    if local.date().isoformat() in (hours.get("holidays") or []):
        return False
    day = hours.get(DAYS[local.weekday()]) or {}
    if not day.get("is_open", True):
        return False
    now_m = local.hour * 60 + local.minute
    close = _minutes(day.get("close", "22:00")) or 24 * 60
    return _minutes(day.get("open", "09:00")) <= now_m < close


def next_open(restaurant, when=None):
    """When the restaurant next takes orders (None if closed for the coming week)."""
    start = (when or timezone.now()).astimezone(_tz(restaurant))
    hours = restaurant.working_hours or {}
    for i in range(8):
        d = (start + timedelta(days=i)).date()
        if d.isoformat() in (hours.get("holidays") or []):
            continue
        day = hours.get(DAYS[d.weekday()]) or {}
        if not day.get("is_open", True):
            continue
        opens = datetime.combine(d, datetime.strptime(day.get("open", "09:00"), "%H:%M").time(), tzinfo=start.tzinfo)
        closes_m = _minutes(day.get("close", "22:00")) or 24 * 60
        if i == 0 and start >= opens:
            if start.hour * 60 + start.minute < closes_m:
                return start
            continue
        return opens
    return None


def delivery_quote(restaurant, lat, lng, subtotal=0):
    if not valid_point(lat, lng):
        raise ValidationError({"latitude": ["Pick a valid delivery location."]})
    if restaurant.latitude is None or restaurant.longitude is None:
        raise ValidationError({"detail": "This restaurant hasn't set its location yet."})
    distance = Decimal(str(round(haversine_km(restaurant.latitude, restaurant.longitude, lat, lng), 2)))
    inside = restaurant.enable_delivery and distance <= restaurant.max_delivery_km
    extra_km = max(Decimal("0"), distance - restaurant.free_delivery_km)
    charge = money(extra_km * restaurant.charge_per_extra_km)
    return {
        "distance_km": float(distance),
        "inside_area": bool(inside),
        "delivery_charge": float(charge),
        "free_delivery_remaining_km": float(max(Decimal("0"), restaurant.free_delivery_km - distance)),
        "estimated_prep_minutes": restaurant.average_prep_minutes,
        "estimated_delivery_minutes": restaurant.average_prep_minutes + int(float(distance) * 3) + 5,
        "minimum_order_amount": float(restaurant.minimum_delivery_order),
        "below_minimum": money(subtotal) < restaurant.minimum_delivery_order,
        "currency_code": restaurant.currency,
        "currency_symbol": "₹" if restaurant.currency == "INR" else restaurant.currency,
    }


def media_url(request, field, fallback=""):
    if field:
        try:
            url = field.url
        except ValueError:
            return fallback or None
        return request.build_absolute_uri(url) if request and url.startswith("/") else url
    return fallback or None


def menu_href(restaurant):
    """Diners open a menu through a table link; use the main branch's first table."""
    table = restaurant.tables.filter(branch__is_main=True).order_by("id").first() or restaurant.tables.order_by("id").first()
    return f"/menu/{table.id}" if table else None


def public_card(restaurant, request, lat=None, lng=None):
    """Restaurant card for discovery, the map and checkout (opening hours come from here, never owner settings)."""
    distance = None
    if valid_point(lat, lng) and restaurant.latitude is not None:
        distance = round(haversine_km(restaurant.latitude, restaurant.longitude, lat, lng), 2)
    inside = bool(restaurant.enable_delivery and distance is not None and distance <= float(restaurant.max_delivery_km))
    offers, rating, reviews = [], None, 0
    from django.apps import apps
    if apps.is_installed("coupons"):
        from coupons.services import public_offer_labels
        offers = public_offer_labels(restaurant)
    if apps.is_installed("reviews"):
        from reviews.services import rating_summary
        rating, reviews = rating_summary(restaurant)
    return {
        "id": restaurant.id, "name": restaurant.name, "slug": restaurant.slug,
        "logo": media_url(request, restaurant.logo), "cover_image": media_url(request, restaurant.cover_image),
        "address": restaurant.address, "city": restaurant.city, "phone": restaurant.phone, "email": restaurant.email,
        "google_business_url": restaurant.google_business_url, "about": restaurant.about,
        "latitude": float(restaurant.latitude) if restaurant.latitude is not None else None,
        "longitude": float(restaurant.longitude) if restaurant.longitude is not None else None,
        "cuisine": restaurant.cuisines, "cuisines": restaurant.cuisines,
        "is_open": is_open_at(restaurant), "working_hours": restaurant.working_hours,
        "distance_km": distance if distance is not None else 0, "inside_delivery_area": inside,
        "free_delivery_km": float(restaurant.free_delivery_km), "charge_per_extra_km": float(restaurant.charge_per_extra_km),
        "minimum_delivery_order": float(restaurant.minimum_delivery_order),
        "pickup_available": restaurant.enable_pickup, "delivery_available": restaurant.enable_delivery,
        "catering_available": restaurant.catering_available, "average_prep_minutes": restaurant.average_prep_minutes,
        "rating": rating, "review_count": reviews, "offers": offers,
        "currency_symbol": "₹" if restaurant.currency == "INR" else restaurant.currency, "href": menu_href(restaurant),
    }
