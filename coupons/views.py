"""Owner coupon management, diner code checks and the offers shown on menus."""
import re
from decimal import Decimal, InvalidOperation

from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.auth import OptionalJWTAuthentication, customer_of
from common.permissions import IsOwnerOrRole
from common.tenancy import get_restaurant
from restaurants.models import Restaurant

from .models import Coupon
from .services import evaluate, visible_offers

CODE = re.compile(r"^[A-Z0-9_-]{3,20}$")


def coupon_out(c):
    return {"id": c.id, "code": c.code, "description": c.description, "discount_type": c.discount_type,
            "value": float(c.value), "minimum_order_amount": float(c.minimum_order_amount),
            "maximum_discount": float(c.maximum_discount) if c.maximum_discount is not None else None,
            "usage_limit": c.usage_limit, "used_count": c.used_count, "per_user_limit": c.per_user_limit,
            "valid_from": c.valid_from, "valid_until": c.valid_until, "applicable_days": c.applicable_days,
            "is_active": c.is_active, "show_on_menu": c.show_on_menu, "audience": c.audience,
            "customer_emails": c.customer_emails, "created_at": c.created_at}


def _dec(v, field, allow_none=False):
    if v in (None, ""):
        if allow_none:
            return None
        return Decimal("0")
    try:
        d = Decimal(str(v))
    except InvalidOperation:
        raise ValidationError({field: ["Enter a number."]})
    if d < 0:
        raise ValidationError({field: ["Can't be negative."]})
    return d.quantize(Decimal("0.01"))


def _int(v, field):
    if v in (None, ""):
        return None
    try:
        n = int(v)
    except (TypeError, ValueError):
        raise ValidationError({field: ["Enter a whole number."]})
    if n < 1:
        raise ValidationError({field: ["Must be at least 1."]})
    return n


def _dt(v, field):
    if v in (None, ""):
        return None
    d = parse_datetime(str(v))
    if d is None:
        raise ValidationError({field: ["Enter a valid date and time."]})
    return d


def _apply(c, d, restaurant):
    if "code" in d:
        c.code = str(d.get("code") or "").strip().upper()
    if "description" in d:
        c.description = str(d.get("description") or "")[:255]
    if "discount_type" in d:
        if d["discount_type"] not in Coupon.Type.values:
            raise ValidationError({"discount_type": ["Pick percent, fixed or buy-one-get-one."]})
        c.discount_type = d["discount_type"]
    if "value" in d:
        c.value = _dec(d["value"], "value")
    if "minimum_order_amount" in d:
        c.minimum_order_amount = _dec(d["minimum_order_amount"], "minimum_order_amount")
    if "maximum_discount" in d:
        c.maximum_discount = _dec(d["maximum_discount"], "maximum_discount", allow_none=True)
    for f in ("usage_limit", "per_user_limit"):
        if f in d:
            setattr(c, f, _int(d[f], f))
    for f in ("valid_from", "valid_until"):
        if f in d:
            setattr(c, f, _dt(d[f], f))
    if "applicable_days" in d:
        days = d.get("applicable_days") or []
        if not isinstance(days, list) or not all(isinstance(x, int) and 0 <= x <= 6 for x in days) or not days:
            raise ValidationError({"applicable_days": ["Pick at least one day."]})
        c.applicable_days = sorted(set(days))
    for f in ("is_active", "show_on_menu"):
        if f in d:
            setattr(c, f, bool(d[f]))
    if "audience" in d:
        if d["audience"] not in Coupon.Audience.values:
            raise ValidationError({"audience": ["Pick who can use this coupon."]})
        c.audience = d["audience"]
    if "customer_emails" in d:
        emails = d.get("customer_emails") or []
        if not isinstance(emails, list):
            raise ValidationError({"customer_emails": ["Send a list of emails."]})
        c.customer_emails = sorted({str(e).strip().lower() for e in emails if str(e).strip()})
    if c.audience != Coupon.Audience.SELECTED:
        c.customer_emails = []

    errors = {}
    if not CODE.match(c.code or ""):
        errors["code"] = ["Use 3–20 letters or numbers."]
    elif Coupon.objects.filter(restaurant=restaurant, code__iexact=c.code).exclude(pk=c.pk).exists():
        errors["code"] = ["This code already exists."]
    if c.discount_type == Coupon.Type.PERCENT and not (0 < c.value <= 100):
        errors["value"] = ["Percent must be between 1 and 100."]
    if c.discount_type == Coupon.Type.FIXED and not c.value > 0:
        errors["value"] = ["Enter an amount."]
    if c.discount_type == Coupon.Type.BOGO:
        c.value = Decimal("0")
    if c.audience == Coupon.Audience.SELECTED and not c.customer_emails:
        errors["customer_emails"] = ["Pick at least one customer."]
    if c.valid_from and c.valid_until and c.valid_until <= c.valid_from:
        errors["valid_until"] = ["End must be after start."]
    if errors:
        raise ValidationError(errors)


class CouponList(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ["manager"]

    def get(self, request):
        r = get_restaurant(request, required=False)
        return Response({"coupons": [coupon_out(c) for c in r.coupons.all()] if r else []})

    def post(self, request):
        r = get_restaurant(request)
        c = Coupon(restaurant=r)
        _apply(c, request.data, r)
        c.save()
        return Response({"coupon": coupon_out(c)}, status=201)


class CouponDetail(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ["manager"]

    def _get(self, request, pk):
        return get_object_or_404(Coupon, pk=pk, restaurant=get_restaurant(request))

    def get(self, request, pk):
        return Response({"coupon": coupon_out(self._get(request, pk))})

    def patch(self, request, pk):
        c = self._get(request, pk)
        _apply(c, request.data, c.restaurant)
        c.save()
        return Response({"coupon": coupon_out(c)})

    put = patch

    def delete(self, request, pk):
        """Coupons are switched off, not removed, so past orders keep their code."""
        c = self._get(request, pk)
        c.is_active = False
        c.save(update_fields=["is_active", "updated_at"])
        return Response(status=204)


def _public_restaurant(pk):
    return get_object_or_404(Restaurant, pk=pk, is_active=True, deleted_at__isnull=True)


@api_view(["POST"])
@authentication_classes([OptionalJWTAuthentication])
@permission_classes([AllowAny])
def validate(request, pk):
    r = _public_restaurant(pk)
    d = request.data
    items = [(i.get("price", 0), i.get("quantity", 1)) for i in (d.get("items") or []) if isinstance(i, dict)]
    coupon, discount = evaluate(r, d.get("code"), d.get("order_amount") or 0, customer_of(request), items)
    return Response({"valid": True, "discount_amount": float(discount), "code": coupon.code})


@api_view(["GET"])
@authentication_classes([OptionalJWTAuthentication])
@permission_classes([AllowAny])
def offers(request, pk):
    return Response(visible_offers(_public_restaurant(pk), customer_of(request)))
