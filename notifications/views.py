import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from common.email import send_email
from common.permissions import IsOwnerOrRole
from common.tenancy import get_restaurant

from .models import TYPES, Notification
from .services import prefs_for

BOOLS = ("browser_enabled", "email_enabled", "whatsapp_enabled", "push_enabled")


def notification_out(n):
    return {"id": n.id, "type": n.type, "title": n.title, "message": n.message, "order_id": n.order_id,
            "read": n.read_at is not None, "created_at": n.created_at}


def prefs_out(p):
    return {"browser_enabled": p.browser_enabled, "email_enabled": p.email_enabled, "email_address": p.email_address,
            "whatsapp_enabled": p.whatsapp_enabled, "whatsapp_number": p.whatsapp_number, "push_enabled": p.push_enabled,
            "events": {t: p.wants(t) for t in TYPES}}


def _roles(view):
    view.cls.allowed_roles = ["manager", "cashier"]
    return view


@_roles
@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def notifications(request):
    r = get_restaurant(request, required=False)
    return Response([notification_out(n) for n in Notification.objects.filter(restaurant=r)[:100]] if r else [])


@_roles
@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def read_one(request, pk):
    n = get_object_or_404(Notification, pk=pk, restaurant=get_restaurant(request))
    if n.read_at is None:
        n.read_at = timezone.now()
        n.save(update_fields=["read_at"])
    return Response(status=204)


@_roles
@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def read_all(request):
    Notification.objects.filter(restaurant=get_restaurant(request), read_at__isnull=True).update(read_at=timezone.now())
    return Response(status=204)


@api_view(["GET", "PATCH"])
@permission_classes([IsOwnerOrRole])
def preferences(request):
    p = prefs_for(get_restaurant(request))
    if request.method == "PATCH":
        d = request.data
        for f in BOOLS:
            if f in d:
                setattr(p, f, bool(d.get(f)))
        if "email_address" in d:
            email = str(d.get("email_address") or "").strip().lower()
            if email:
                try:
                    validate_email(email)
                except DjangoValidationError:
                    raise ValidationError({"email_address": ["Enter a valid email."]})
            p.email_address = email
        if "whatsapp_number" in d:
            p.whatsapp_number = str(d.get("whatsapp_number") or "").strip()[:20]
            if p.whatsapp_number and len(re.sub(r"\D", "", p.whatsapp_number)) < 8:
                raise ValidationError({"whatsapp_number": ["Enter a valid WhatsApp number."]})
        if isinstance(d.get("events"), dict):
            p.events = {**p.events, **{k: bool(v) for k, v in d["events"].items() if k in TYPES}}
        p.save()
    return Response(prefs_out(p))


preferences.cls.allowed_roles = ["manager"]


@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def test(request):
    r = get_restaurant(request)
    channel = request.data.get("channel")
    if channel == "email":
        p = prefs_for(r)
        to = p.email_address or r.email
        if not to:
            raise ValidationError({"detail": "Add an email address first."})
        return Response({"ok": send_email(to, f"{r.name}: test alert", "Your Zen QR Menu email alerts are working.")})
    if channel in ("whatsapp", "push"):
        raise ValidationError({"detail": f"{channel.capitalize()} alerts aren't available yet."})
    raise ValidationError({"channel": ["Pick email, WhatsApp or push."]})


test.cls.allowed_roles = ["manager"]
