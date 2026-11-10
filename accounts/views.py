"""Owner sign-up, email confirmation, login (username or email), Google sign-in and password reset."""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from common.email import send_email
from common.tenancy import is_customer

from .models import OwnerAccount

log = logging.getLogger(__name__)
User = get_user_model()
VERIFY_SALT = "zen.verify-email"


class AuthThrottle(AnonRateThrottle):
    """Per-IP limit on sign-in style endpoints (they run without authentication)."""
    scope = "auth"


def user_out(user):
    return {"id": user.id, "username": user.username, "email": user.email,
            "first_name": user.first_name, "last_name": user.last_name}


def tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def account(user):
    acc, _ = OwnerAccount.objects.get_or_create(user=user, defaults={"email_verified": user.is_staff or user.is_superuser})
    return acc


def send_verification(user):
    token = signing.dumps({"user": user.pk, "email": user.email}, salt=VERIFY_SALT)
    link = f"{settings.BACKEND_URL}/api/verify-email/?token={token}"
    send_email(
        user.email, "Confirm your Zen QR Menu email",
        f"Hi {user.username},\n\nConfirm your email to start using Zen QR Menu:\n{link}\n\nThis link works for 3 days.",
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def register(request):
    d = request.data
    username = str(d.get("username", "")).strip()
    email = str(d.get("email", "")).strip().lower()
    p1 = d.get("password1") or d.get("password") or ""
    p2 = d.get("password2") or d.get("confirm_password") or p1
    errors = {}
    if not username:
        errors["username"] = ["Choose a username."]
    elif User.objects.filter(username__iexact=username).exists():
        errors["username"] = ["This username is taken."]
    if not email or "@" not in email:
        errors["email"] = ["Enter a valid email address."]
    elif User.objects.filter(email__iexact=email, customer_profile__isnull=True).exists():
        # Diner accounts may share an email with a restaurant account; the two never mix.
        errors["email"] = ["An account with this email already exists."]
    if p1 != p2:
        errors["password2"] = ["Passwords do not match."]
    elif p1:
        try:
            password_validation.validate_password(p1, User(username=username, email=email))
        except DjangoValidationError as e:
            errors["password1"] = list(e.messages)
    else:
        errors["password1"] = ["Choose a password."]
    if errors:
        first = next(iter(errors.values()))[0]
        return Response({"success": False, "errors": errors, "message": first, "error": first}, status=400)
    with transaction.atomic():
        user = User.objects.create_user(username=username, email=email, password=p1)
        OwnerAccount.objects.create(user=user)
    transaction.on_commit(lambda: send_verification(user))
    return Response({"success": True, "message": "Account created. Check your email to confirm it."}, status=201)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def verify_email(request):
    try:
        data = signing.loads(request.query_params.get("token", ""), salt=VERIFY_SALT, max_age=3 * 24 * 3600)
        user = User.objects.get(pk=data["user"], email__iexact=data["email"])
    except (signing.BadSignature, User.DoesNotExist, KeyError, TypeError):
        return HttpResponseRedirect(f"{settings.FRONTEND_URL}/login?verified=0")
    acc = account(user)
    if not acc.email_verified:
        acc.email_verified = True
        acc.verified_at = timezone.now()
        acc.save(update_fields=["email_verified", "verified_at"])
    return HttpResponseRedirect(f"{settings.FRONTEND_URL}/login?verified=1")


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def resend_verification(request):
    email = str(request.data.get("email", "")).strip()
    user = User.objects.filter(email__iexact=email, customer_profile__isnull=True).first() if email else None
    if user and not account(user).email_verified:
        send_verification(user)
    # Same answer either way so nobody can probe which emails have accounts.
    return Response({"success": True, "message": "If that email needs confirming, a new link is on its way."})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def login(request):
    ident = str(request.data.get("username", "")).strip()
    password = request.data.get("password") or ""
    owners = User.objects.filter(customer_profile__isnull=True)
    user = owners.filter(Q(username__iexact=ident) | Q(email__iexact=ident)).order_by("id").first() if ident else None
    if user is None or not user.check_password(password) or not user.is_active:
        return Response({"success": False, "error": "Invalid username or password.", "message": "Invalid username or password."}, status=400)
    if is_customer(user) and not hasattr(user, "owner_account"):
        msg = "This is a diner account. Use diner sign-in instead."
        return Response({"success": False, "error": msg, "message": msg}, status=400)
    if not account(user).email_verified:
        return Response({"success": False, "error": "Email not verified", "message": "Email not verified", "email": user.email}, status=403)
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])
    return Response({"success": True, "user": user_out(user), **tokens_for(user)})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def refresh(request):
    try:
        token = RefreshToken(request.data.get("refresh", ""))
        return Response({"access": str(token.access_token)})
    except TokenError:
        return Response({"detail": "Session expired. Please log in again.", "code": "token_not_valid"}, status=401)


@api_view(["POST"])
@permission_classes([AllowAny])
def logout(request):
    try:
        RefreshToken(request.data.get("refresh", "")).blacklist()
    except TokenError:
        pass
    return Response({"success": True})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user(request):
    return Response({"authenticated": True, "user": user_out(request.user)})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def google(request):
    if not settings.GOOGLE_CLIENT_ID:
        return Response({"detail": "Google sign-in isn't set up on the server yet."}, status=503)
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token
    try:
        info = google_id_token.verify_oauth2_token(request.data.get("id_token") or request.data.get("credential") or "",
                                                   google_requests.Request(), settings.GOOGLE_CLIENT_ID)
    except ValueError:
        return Response({"detail": "Google sign-in failed. Please try again."}, status=400)
    if not info.get("email_verified"):
        return Response({"detail": "Your Google email isn't verified."}, status=400)
    email = info["email"].lower()
    with transaction.atomic():
        user = User.objects.filter(email__iexact=email, customer_profile__isnull=True).first()
        if user is None:
            base = email.split("@")[0][:120] or "owner"
            username, n = base, 1
            while User.objects.filter(username__iexact=username).exists():
                n += 1
                username = f"{base}{n}"
            user = User.objects.create_user(username=username, email=email, first_name=info.get("given_name", ""),
                                            last_name=info.get("family_name", ""))
            user.set_unusable_password()
            user.save()
        elif is_customer(user) and not hasattr(user, "owner_account"):
            return Response({"detail": "This email belongs to a diner account. Use diner sign-in instead."}, status=400)
        acc = account(user)
        acc.email_verified, acc.google_sub = True, info.get("sub", "")
        acc.verified_at = acc.verified_at or timezone.now()
        acc.save()
    return Response({"success": True, "user": user_out(user), **tokens_for(user)})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def password_reset(request):
    email = str(request.data.get("email", "")).strip()
    user = User.objects.filter(email__iexact=email, is_active=True, customer_profile__isnull=True).first() if email else None
    if user:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
        send_email(user.email, "Reset your Zen QR Menu password",
                   f"Hi {user.username},\n\nReset your password here:\n{link}\n\nIf you didn't ask for this, ignore this email.")
    return Response({"success": True, "message": "If an account uses that email, a reset link is on its way."})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def password_reset_confirm(request):
    d = request.data
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(d.get("uid", ""))))
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None
    if user is None or not default_token_generator.check_token(user, d.get("token", "")):
        return Response({"success": False, "error": "This reset link is invalid or has expired.", "message": "This reset link is invalid or has expired."}, status=400)
    p1, p2 = d.get("new_password1", ""), d.get("new_password2", "")
    if p1 != p2:
        return Response({"success": False, "errors": {"new_password2": ["Passwords do not match."]}, "error": "Passwords do not match.", "message": "Passwords do not match."}, status=400)
    try:
        password_validation.validate_password(p1, user)
    except DjangoValidationError as e:
        return Response({"success": False, "errors": {"new_password1": list(e.messages)}, "error": e.messages[0], "message": e.messages[0]}, status=400)
    user.set_password(p1)
    user.save()
    acc = account(user)
    if not acc.email_verified:  # resetting by email proves they own it
        acc.email_verified, acc.verified_at = True, timezone.now()
        acc.save()
    return Response({"success": True, "message": "Password updated. You can log in now."})
