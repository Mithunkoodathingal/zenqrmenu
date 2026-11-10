"""Diner sign-in with an emailed code, profile, saved addresses and order history."""
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from common.email import send_email
from common.geo import valid_point
from restaurants.services import media_url

from .models import CustomerAddress, CustomerProfile, EmailCode

User = get_user_model()
PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}


class IsCustomer(BasePermission):
    message = "Sign in with your diner account."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and hasattr(request.user, "customer_profile"))


class OtpThrottle(AnonRateThrottle):
    scope = "otp"


def customer_tokens(user):
    """Diner sessions last longer than owner ones (the website keeps diners signed in without refreshing)."""
    refresh = RefreshToken.for_user(user)
    refresh["role"] = "customer"
    access = refresh.access_token
    access.set_exp(lifetime=timedelta(days=settings.CUSTOMER_SESSION_DAYS))
    return {"access": str(access), "refresh": str(refresh)}


def me_out(p, request=None):
    return {"id": p.id, "name": p.name, "email": p.email, "phone": p.phone, "email_verified": p.email_verified,
            "marketing_opt_in": p.marketing_opt_in, "marketing_consent_at": p.marketing_consent_at,
            "photo_url": media_url(request, p.photo)}


def address_out(a):
    return {"id": a.id, "label": a.label, "recipient_name": a.recipient_name, "phone": a.phone, "house": a.house,
            "street": a.street, "area": a.area, "city": a.city, "state": a.state, "postal_code": a.postal_code,
            "latitude": float(a.latitude) if a.latitude is not None else None,
            "longitude": float(a.longitude) if a.longitude is not None else None,
            "is_default": a.is_default, "full_address": a.one_line()}


def _email(v):
    v = str(v or "").strip().lower()
    if not v or "@" not in v or len(v) > 254 or " " in v:
        raise ValidationError({"email": ["Enter a valid email address."]})
    return v


def _phone(v, field="phone", required=False):
    v = str(v or "").strip()
    digits = "".join(c for c in v if c.isdigit())
    if not v and not required:
        return ""
    if not (10 <= len(digits) <= 15):
        raise ValidationError({field: ["Enter a valid phone number (10–15 digits)."]})
    return v


# ─── Sign-in ──────────────────────────────────────────────────────────────

@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([OtpThrottle])
def request_code(request):
    email = _email(request.data.get("email"))
    intent = request.data.get("intent") or "login"
    exists = CustomerProfile.objects.filter(email=email).exists()
    if intent == "register" and exists:
        raise ValidationError({"email": ["This email already has an account. Sign in instead."]})
    if intent == "login" and not exists:
        raise ValidationError({"email": ["No account for this email yet. Create one instead."]})
    if EmailCode.objects.filter(email=email, created_at__gte=timezone.now() - timedelta(seconds=60)).exists():
        return Response({"detail": "Please wait a minute before asking for another code."}, status=429)
    code = EmailCode.issue(email)
    sent = send_email(email, "Your Zen QR Menu sign-in code",
                      f"Your sign-in code is {code}. It expires in {EmailCode.VALID_MINUTES} minutes.\n\n"
                      "If you didn't ask for this, you can ignore this email.")
    if not sent:
        return Response({"detail": "We couldn't send the email right now. Try again shortly."}, status=503)
    return Response({"detail": "Code sent."})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([OtpThrottle])
def verify_code(request):
    d = request.data
    email = _email(d.get("email"))
    code = str(d.get("code") or "").strip()
    entry = EmailCode.objects.filter(email=email, used_at__isnull=True).order_by("-created_at").first()
    if entry is None or not entry.usable():
        raise ValidationError({"code": ["This code has expired. Ask for a new one."]})
    if not secrets.compare_digest(entry.code_hash, EmailCode.hash(code)):
        entry.attempts += 1
        entry.save(update_fields=["attempts"])
        left = max(EmailCode.MAX_ATTEMPTS - entry.attempts, 0)
        raise ValidationError({"code": [f"Wrong code. {left} tries left." if left else "Too many wrong tries. Ask for a new code."]})
    name = str(d.get("name") or "").strip()[:150]
    phone = _phone(d.get("phone"))
    with transaction.atomic():
        entry.used_at = timezone.now()
        entry.save(update_fields=["used_at"])
        profile = CustomerProfile.objects.select_related("user").filter(email=email).first()
        if profile is None:
            user = User.objects.create_user(username=f"cust_{secrets.token_hex(8)}", email=email)
            user.set_unusable_password()
            user.save()
            profile = CustomerProfile(user=user, email=email, name=name or email.split("@")[0], phone=phone, email_verified=True)
            profile.set_marketing(bool(d.get("marketing_opt_in")))
            profile.save()
        else:
            profile.email_verified = True
            if name and not profile.name:
                profile.name = name
            if phone and not profile.phone:
                profile.phone = phone
            profile.save()
    return Response({**customer_tokens(profile.user), "customer": me_out(profile, request)})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def refresh(request):
    try:
        token = RefreshToken(request.data.get("refresh", ""))
        user = User.objects.get(pk=token["user_id"])
        if not hasattr(user, "customer_profile"):
            raise TokenError("not a diner")
        access = token.access_token
        access.set_exp(lifetime=timedelta(days=settings.CUSTOMER_SESSION_DAYS))
        return Response({"access": str(access)})
    except (TokenError, User.DoesNotExist, KeyError):
        return Response({"detail": "Session expired. Please sign in again.", "code": "token_not_valid"}, status=401)


# ─── Profile ──────────────────────────────────────────────────────────────

class MeView(APIView):
    permission_classes = [IsCustomer]

    def get(self, request):
        return Response(me_out(request.user.customer_profile, request))

    def patch(self, request):
        p = request.user.customer_profile
        d = request.data
        if "name" in d:
            name = str(d.get("name") or "").strip()
            if not name:
                raise ValidationError({"name": ["Enter your name."]})
            p.name = name[:150]
        if "phone" in d:
            p.phone = _phone(d.get("phone"))
        if "marketing_opt_in" in d:
            p.set_marketing(str(d.get("marketing_opt_in")).lower() in {"true", "1", "on", "yes"})
        if "profile_photo" in d:
            f = request.FILES.get("profile_photo")
            if f is None:
                if p.photo:
                    p.photo.delete(save=False)
                p.photo = None
            else:
                if f.content_type not in PHOTO_TYPES or f.size > 5 * 1024 * 1024:
                    raise ValidationError({"profile_photo": ["Use a JPG, PNG or WebP photo under 5 MB."]})
                p.photo = f
        p.save()
        return Response(me_out(p, request))


# ─── Addresses ────────────────────────────────────────────────────────────

ADDRESS_FIELDS = ["label", "recipient_name", "phone", "house", "street", "area", "city", "state", "postal_code"]


def _apply_address(a, d, creating):
    for f in ADDRESS_FIELDS:
        if f in d:
            setattr(a, f, str(d.get(f) or "").strip()[:200])
    errors = {}
    for f, msg in [("recipient_name", "Enter who receives the order."), ("house", "Enter the house or flat."), ("city", "Enter the city.")]:
        if not getattr(a, f):
            errors[f] = [msg]
    try:
        a.phone = _phone(a.phone, required=True)
    except ValidationError as e:
        errors.update(e.detail)
    if "latitude" in d or "longitude" in d:
        lat, lng = d.get("latitude"), d.get("longitude")
        if lat in (None, "") and lng in (None, ""):
            a.latitude = a.longitude = None
        elif not valid_point(lat, lng):
            errors["latitude"] = ["Pick the location on the map."]
        else:
            a.latitude, a.longitude = round(float(lat), 6), round(float(lng), 6)
    a.label = a.label or "Home"
    if errors:
        raise ValidationError(errors)


class AddressList(APIView):
    permission_classes = [IsCustomer]

    def get(self, request):
        return Response([address_out(a) for a in request.user.customer_profile.addresses.all()])

    def post(self, request):
        p = request.user.customer_profile
        a = CustomerAddress(customer=p)
        _apply_address(a, request.data, True)
        with transaction.atomic():
            a.is_default = not p.addresses.filter(is_default=True).exists()
            a.save()
        return Response(address_out(a), status=201)


class AddressDetail(APIView):
    permission_classes = [IsCustomer]

    def _get(self, request, pk):
        return get_object_or_404(CustomerAddress, pk=pk, customer=request.user.customer_profile)

    def get(self, request, pk):
        return Response(address_out(self._get(request, pk)))

    def patch(self, request, pk):
        a = self._get(request, pk)
        _apply_address(a, request.data, False)
        a.save()
        return Response(address_out(a))

    put = patch

    def delete(self, request, pk):
        a = self._get(request, pk)
        with transaction.atomic():
            was_default = a.is_default
            a.delete()
            if was_default:
                nxt = request.user.customer_profile.addresses.order_by("-updated_at").first()
                if nxt:
                    nxt.is_default = True
                    nxt.save(update_fields=["is_default"])
        return Response(status=204)


@api_view(["POST"])
@permission_classes([IsCustomer])
def set_default(request, pk):
    p = request.user.customer_profile
    a = get_object_or_404(CustomerAddress, pk=pk, customer=p)
    with transaction.atomic():
        p.addresses.filter(is_default=True).exclude(pk=a.pk).update(is_default=False)
        a.is_default = True
        a.save(update_fields=["is_default"])
    return Response(address_out(a))


# ─── Orders ───────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsCustomer])
def my_orders(request):
    from orders.serializers import customer_order_summary
    orders = request.user.customer_profile.orders.select_related("restaurant").order_by("-created_at")[:100]
    return Response([customer_order_summary(o) for o in orders])


@api_view(["GET"])
@permission_classes([IsCustomer])
def my_order(request, pk):
    from orders.serializers import customer_order_summary
    o = get_object_or_404(request.user.customer_profile.orders.select_related("restaurant"), pk=pk)
    out = customer_order_summary(o)
    out["items"] = [{"name": i.name, "quantity": i.quantity, "price": float(i.unit_price), "addons": i.addons}
                    for i in o.items.all()]
    out.update({"subtotal": float(o.subtotal), "discount_amount": float(o.discount_amount), "delivery_charge": float(o.delivery_charge),
                "tip_amount": float(o.tip_amount), "tax_amount": float(o.tax_amount), "customer_address": o.customer_address,
                "scheduled_time": o.scheduled_time, "payment_method": o.payment_method, "payment_status": o.payment_status})
    return Response(out)
