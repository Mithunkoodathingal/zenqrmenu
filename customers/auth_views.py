"""Permanent diner accounts: email + password sign-in. The emailed 6-digit code only activates a new account.

Replies never reveal whether an email is registered (except the password-setup hint for verified legacy
code-only accounts, which the diner needs to move to a password). Codes, tokens and passwords are never
returned or logged.
"""
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from common.email import send_email

from .models import CustomerProfile, EmailCode
from .views import IsCustomer, OtpThrottle, _email, _phone, customer_tokens, me_out

User = get_user_model()
LOCK_AFTER = 5
LOCK_SECONDS = 15 * 60
RESEND_SECONDS = 60
SENT = "If this email can be used, we've sent a 6-digit code to it."


def _password(pw, user=None):
    pw = str(pw or "")
    problems = []
    if len(pw) < 8:
        problems.append("Use at least 8 characters.")
    if not any(c.isalpha() for c in pw) or not any(c.isdigit() for c in pw):
        problems.append("Include at least one letter and one number.")
    try:
        validate_password(pw, user)
    except DjangoValidationError as e:
        problems += [m for m in e.messages if m not in problems]
    if problems:
        raise ValidationError({"password": problems})
    return pw


def _send_code(email):
    code = EmailCode.issue(email)
    return send_email(email, "Verify your email — OrbitDine",
                      f"Your verification code is {code}. It expires in {EmailCode.VALID_MINUTES} minutes.\n\n"
                      "If you didn't create an account, you can ignore this email.")


def _too_soon(email):
    return EmailCode.objects.filter(email=email, created_at__gte=timezone.now() - timezone.timedelta(seconds=RESEND_SECONDS)).exists()


def _ip(request):
    return (request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR") or "").split(",")[0].strip()


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([OtpThrottle])
def register(request):
    d = request.data
    email = _email(d.get("email"))
    name = str(d.get("name") or "").strip()[:150]
    if len(name) < 2:
        raise ValidationError({"name": ["Enter your name."]})
    phone = _phone(d.get("phone"))
    password = _password(d.get("password"))
    profile = CustomerProfile.objects.select_related("user").filter(email=email).first()
    if profile and profile.email_verified:
        # Same reply as a new sign-up; the owner of the inbox learns what happened.
        send_email(email, "You already have an OrbitDine account",
                   "Someone tried to create an account with this email. You already have one — sign in, or use "
                   f"'Forgot password' at {settings.FRONTEND_URL}/account/login to set a new password.")
        return Response({"detail": SENT, "expires_minutes": EmailCode.VALID_MINUTES})
    with transaction.atomic():
        if profile is None:
            user = User.objects.create_user(username=f"cust_{secrets.token_hex(8)}", email=email, is_active=False)
            profile = CustomerProfile(user=user, email=email)
        user = profile.user
        user.set_password(password)
        user.is_active = False
        user.save()
        profile.name, profile.phone = name, phone
        profile.set_marketing(bool(d.get("marketing_opt_in")))
        profile.save()
    if _too_soon(email):
        return Response({"detail": "Please wait a minute before asking for another code."}, status=429)
    if not _send_code(email):
        return Response({"detail": "We couldn't send the email right now. Try again shortly."}, status=503)
    return Response({"detail": SENT, "expires_minutes": EmailCode.VALID_MINUTES})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([OtpThrottle])
def resend_code(request):
    email = _email(request.data.get("email"))
    if _too_soon(email):
        return Response({"detail": "Please wait a minute before asking for another code."}, status=429)
    profile = CustomerProfile.objects.filter(email=email, email_verified=False).first()
    if profile and not _send_code(email):
        return Response({"detail": "We couldn't send the email right now. Try again shortly."}, status=503)
    return Response({"detail": SENT})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([OtpThrottle])
def verify_email(request):
    email = _email(request.data.get("email"))
    code = str(request.data.get("code") or "").strip()
    profile = CustomerProfile.objects.select_related("user").filter(email=email, email_verified=False).first()
    entry = EmailCode.objects.filter(email=email, used_at__isnull=True).order_by("-created_at").first()
    if profile is None or entry is None or not entry.usable():
        raise ValidationError({"code": ["This code has expired. Ask for a new one."]})
    if not secrets.compare_digest(entry.code_hash, EmailCode.hash(code)):
        entry.attempts += 1
        entry.save(update_fields=["attempts"])
        left = max(EmailCode.MAX_ATTEMPTS - entry.attempts, 0)
        raise ValidationError({"code": [f"Wrong code. {left} tries left." if left else "Too many wrong tries. Ask for a new code."]})
    with transaction.atomic():
        entry.used_at = timezone.now()
        entry.save(update_fields=["used_at"])
        profile.email_verified = True
        profile.save(update_fields=["email_verified", "updated_at"])
        profile.user.is_active = True
        profile.user.save(update_fields=["is_active"])
    return Response({**customer_tokens(profile.user), "customer": me_out(profile, request)})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login(request):
    email = _email(request.data.get("email"))
    password = str(request.data.get("password") or "")
    key = f"diner-login:{email}:{_ip(request)}"
    if cache.get(key, 0) >= LOCK_AFTER:
        return Response({"detail": "Too many attempts. Try again in 15 minutes or reset your password."}, status=429)
    profile = CustomerProfile.objects.select_related("user").filter(email=email).first()
    user = profile.user if profile else None
    if user and profile.email_verified and not user.has_usable_password():
        return Response({"detail": "This account doesn't have a password yet. We can email you a link to set one.",
                         "code": "password_not_set"}, status=400)
    if not user or not profile.email_verified or not user.is_active or not user.check_password(password):
        cache.set(key, cache.get(key, 0) + 1, LOCK_SECONDS)
        return Response({"detail": "Email or password is incorrect."}, status=400)
    cache.delete(key)
    return Response({**customer_tokens(user), "customer": me_out(profile, request)})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([OtpThrottle])
def forgot_password(request):
    email = _email(request.data.get("email"))
    profile = CustomerProfile.objects.select_related("user").filter(email=email, email_verified=True).first()
    if profile:
        user = profile.user
        link = (f"{settings.FRONTEND_URL}/account/reset-password?uid={urlsafe_base64_encode(force_bytes(user.pk))}"
                f"&token={default_token_generator.make_token(user)}")
        send_email(email, "Set your OrbitDine password",
                   f"Use this link to set a new password (valid for 1 hour):\n\n{link}\n\n"
                   "If you didn't ask for this, you can ignore this email.")
    return Response({"detail": "If an account exists for this email, we've sent a link to set a new password."})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([OtpThrottle])
def reset_password(request):
    bad = Response({"detail": "This link is invalid or has expired. Ask for a new one."}, status=400)
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(str(request.data.get("uid") or ""))))
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return bad
    profile = getattr(user, "customer_profile", None)
    # Reset never activates an unverified account.
    if profile is None or not profile.email_verified or not default_token_generator.check_token(user, str(request.data.get("token") or "")):
        return bad
    user.set_password(_password(request.data.get("password"), user))
    user.save(update_fields=["password"])
    return Response({"detail": "Password set. You can now sign in."})


@api_view(["POST"])
@permission_classes([IsCustomer])
def change_password(request):
    user = request.user
    if user.has_usable_password() and not user.check_password(str(request.data.get("current_password") or "")):
        raise ValidationError({"current_password": ["Your current password is incorrect."]})
    user.set_password(_password(request.data.get("new_password"), user))
    user.save(update_fields=["password"])
    return Response({"detail": "Password changed."})
