from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from common.email import send_email
from common.permissions import IsOwnerOrRole
from common.tenancy import get_restaurant
from coupons.models import Coupon
from customers.models import CustomerProfile
from customers.views import IsCustomer

from .models import Campaign
from .services import audience, can_email, restaurant_customers, unsubscribe_url

ROLES = ["manager"]


def customer_out(c):
    return {"id": c.id, "name": c.name, "email": c.email, "phone": c.phone, "marketing_opt_in": c.marketing_opt_in,
            "unsubscribed_at": c.unsubscribed_at, "can_email": can_email(c), "orders": c.n or 0,
            "spend": float(c.spend or 0), "last_order_at": c.last}


def campaign_out(c):
    return {"id": c.id, "name": c.name, "subject": c.subject, "body": c.body, "audience": c.audience,
            "customer_emails": c.customer_emails, "coupon_id": c.coupon_id, "status": c.status, "sent_at": c.sent_at,
            "recipients": c.recipients, "skipped": c.skipped, "created_at": c.created_at}


def _apply(c, d, creating):
    errors = {}
    for f, n, label in (("name", 120, "a campaign name"), ("subject", 150, "a subject line")):
        if f in d or creating:
            setattr(c, f, str(d.get(f) or "").strip()[:n])
            if not getattr(c, f):
                errors[f] = [f"Enter {label}."]
    if "body" in d or creating:
        c.body = str(d.get("body") or "").strip()[:5000]
        if len(c.body) < 10:
            errors["body"] = ["Write at least 10 characters."]
    if "audience" in d:
        if d.get("audience") not in Campaign.Audience.values:
            errors["audience"] = ["Pick who receives it."]
        else:
            c.audience = d.get("audience")
    if "customer_emails" in d:
        emails = d.get("customer_emails") or []
        c.customer_emails = sorted({str(e).strip().lower() for e in emails if str(e).strip()})[:500] if isinstance(emails, list) else []
    if c.audience == Campaign.Audience.SELECTED and not c.customer_emails:
        errors["customer_emails"] = ["Pick at least one customer."]
    if "coupon_id" in d:
        cid = d.get("coupon_id")
        c.coupon = Coupon.objects.filter(pk=cid, restaurant=c.restaurant).first() if cid not in (None, "") else None
        if cid not in (None, "") and c.coupon is None:
            errors["coupon_id"] = ["That coupon isn't yours."]
    if errors:
        raise ValidationError(errors)
    c.save()
    return c


class Customers(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ROLES

    def get(self, request):
        r = get_restaurant(request, required=False)
        return Response([customer_out(c) for c in restaurant_customers(r).order_by("-last")] if r else [])


class CampaignList(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ROLES

    def get(self, request):
        r = get_restaurant(request, required=False)
        return Response([campaign_out(c) for c in Campaign.objects.filter(restaurant=r)] if r else [])

    def post(self, request):
        return Response(campaign_out(_apply(Campaign(restaurant=get_restaurant(request)), request.data, True)), status=201)


class CampaignDetail(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ROLES

    def _get(self, request, pk):
        return get_object_or_404(Campaign, pk=pk, restaurant=get_restaurant(request))

    def patch(self, request, pk):
        c = self._get(request, pk)
        if c.status == "sent":
            raise ValidationError({"detail": "A sent campaign can't be changed."})
        return Response(campaign_out(_apply(c, request.data, False)))

    def delete(self, request, pk):
        self._get(request, pk).delete()
        return Response(status=204)


def _roles(view):
    view.cls.allowed_roles = ROLES
    return view


@_roles
@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def preview(request):
    who, skipped = audience(get_restaurant(request), request.data.get("audience"), request.data.get("customer_emails"))
    return Response({"recipients": [c.email for c in who], "skipped": len(skipped), "skipped_reasons": skipped})


@_roles
@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def send(request, pk):
    r = get_restaurant(request)
    with transaction.atomic():
        c = get_object_or_404(Campaign.objects.select_for_update(), pk=pk, restaurant=r)
        if c.status == "sent":
            raise ValidationError({"detail": "This campaign was already sent."})
        who, skipped = audience(r, c.audience, c.customer_emails)
        if not who:
            raise ValidationError({"detail": "Nobody in this audience has agreed to marketing emails."})
        c.status, c.sent_at, c.recipients, c.skipped = "sent", timezone.now(), [p.email for p in who], len(skipped)
        c.save()
        if c.coupon and c.coupon.audience == "selected":
            c.coupon.customer_emails = sorted(set(c.coupon.customer_emails or []) | set(c.recipients))
            c.coupon.save(update_fields=["customer_emails"])
    code = f"\n\nUse code {c.coupon.code} on your next order." if c.coupon else ""
    for p in who:  # one email each, so nobody sees another diner's address
        link = unsubscribe_url(p)
        send_email(p.email, c.subject, f"{c.body}{code}\n\n— {r.name}\n\nDon't want these emails? Unsubscribe: {link}")
    return Response(campaign_out(c))


@_roles
@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def unsubscribe_link(request, email):
    r = get_restaurant(request)
    p = restaurant_customers(r).filter(email__iexact=email).first()
    if p is None:
        return Response({"detail": "Not one of your customers."}, status=404)
    return Response({"url": unsubscribe_url(p)})


class UnsubscribeThrottle(AnonRateThrottle):
    rate = "30/min"


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@throttle_classes([UnsubscribeThrottle])
def unsubscribe(request, token):
    p = get_object_or_404(CustomerProfile, unsubscribe_token=token)
    if request.method == "POST" and p.unsubscribed_at is None:
        p.set_marketing(False)
        p.unsubscribed_at = timezone.now()
        p.save(update_fields=["marketing_opt_in", "marketing_consent_at", "unsubscribed_at"])
    masked = p.email[0] + "•••" + p.email[p.email.index("@"):]
    return Response({"email": masked, "unsubscribed": p.unsubscribed_at is not None})


@api_view(["POST"])
@permission_classes([IsCustomer])
def consent(request):
    p = request.user.customer_profile
    p.set_marketing(str(request.data.get("marketing_opt_in")).lower() in {"true", "1"})
    if not p.marketing_opt_in and p.unsubscribed_at is None:
        p.unsubscribed_at = timezone.now()
    p.save(update_fields=["marketing_opt_in", "marketing_consent_at", "unsubscribed_at"])
    return Response({"marketing_opt_in": p.marketing_opt_in, "marketing_consent_at": p.marketing_consent_at})
