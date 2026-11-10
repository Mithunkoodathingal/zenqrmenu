"""Called by orders: riders are freed when an order ends, and orders show their rider and live progress."""
from .models import DeliveryAssignment
from .services import active_assignment, end_assignment, eta, photo_url


def after_status_change(order, old, new):
    if new not in ("completed", "cancelled"):
        return
    a = active_assignment(order)
    if a is not None:
        end_assignment(a, DeliveryAssignment.Status.DELIVERED if new == "completed" else DeliveryAssignment.Status.CANCELLED)


def order_fields(order):
    a = active_assignment(order) if order.is_open else (
        order.delivery_assignments.filter(status="delivered").select_related("partner").first())
    if a is None:
        return {}
    p = a.partner
    out = {
        "delivery_partner": {"id": p.id, "name": p.full_name, "phone": p.phone, "photo": photo_url(p.profile_photo),
                             "vehicle_type": p.vehicle_type, "vehicle_number": p.vehicle_number,
                             "latitude": float(p.latitude) if p.latitude is not None else None,
                             "longitude": float(p.longitude) if p.longitude is not None else None,
                             "updated_at": p.last_location_update},
        "delivery_partner_id": p.id, "assigned_at": a.assigned_at, "delivery_status": a.status,
    }
    if a.status == DeliveryAssignment.Status.STARTED:
        minutes, km = eta(order, p)
        out.update({"tracking_status": "out_for_delivery", "eta_minutes": minutes, "remaining_distance_km": km})
    return out
