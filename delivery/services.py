import math

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from common.geo import haversine_km

from .models import DeliveryAssignment

ACTIVE = (DeliveryAssignment.Status.ASSIGNED, DeliveryAssignment.Status.STARTED)
RIDER_KMH = 20


def photo_url(field):
    """Absolute photo address (the tracking page shows it as-is)."""
    if not field:
        return None
    try:
        url = field.url
    except ValueError:
        return None
    return f"{settings.BACKEND_URL.rstrip('/')}{url}" if url.startswith("/") else url


def active_assignment(order):
    return order.delivery_assignments.filter(status__in=ACTIVE).select_related("partner").first()


def refresh_availability(partner):
    """A rider with no trips in hand is free again."""
    busy = partner.assignments.filter(status__in=ACTIVE).exists()
    if partner.is_available == busy:
        partner.is_available = not busy
        partner.save(update_fields=["is_available"])


@transaction.atomic
def end_assignment(a, status):
    a.status = status
    a.ended_at = timezone.now()
    if status == DeliveryAssignment.Status.DELIVERED:
        a.delivered_at = a.ended_at
    a.save(update_fields=["status", "ended_at", "delivered_at"])
    refresh_availability(a.partner)


def eta(order, partner):
    if None in (partner.latitude, partner.longitude, order.delivery_latitude, order.delivery_longitude):
        return None, None
    km = round(haversine_km(partner.latitude, partner.longitude, order.delivery_latitude, order.delivery_longitude), 2)
    return math.ceil(km / RIDER_KMH * 60) + 2, km
