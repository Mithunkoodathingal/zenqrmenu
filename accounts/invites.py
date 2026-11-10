"""Logins for staff and delivery partners. The owner adds them; they get an email to choose a password."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.exceptions import ValidationError

from common.email import send_email

User = get_user_model()


def login_for(email, first_name, last_name, restaurant, what, current=None):
    """Return the User for this staff member/partner, creating one (and emailing a set-password link) if needed.

    An email already used by a diner, an owner, or someone else's staff can't be reused.
    """
    email = (email or "").strip().lower()
    if not email:
        return current
    if current is not None and current.email.lower() == email:
        return current
    existing = User.objects.filter(email__iexact=email).first()
    if existing is not None and existing != current:
        raise ValidationError({"email": ["This email already has a Zen QR Menu account. Use a different email."]})
    if current is not None:
        current.email = current.username = email
        current.save(update_fields=["email", "username"])
        invite(current, restaurant, what)
        return current
    user = User(username=email, email=email, first_name=(first_name or "")[:150], last_name=(last_name or "")[:150])
    user.set_unusable_password()
    user.save()
    invite(user, restaurant, what)
    return user


def invite(user, restaurant, what):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
    send_email(user.email, f"You've been added to {restaurant.name} on Zen QR Menu",
               f"Hi {user.first_name or 'there'},\n\n{restaurant.name} added you as {what}. Choose your password here:\n{link}\n\n"
               f"Then log in at {settings.FRONTEND_URL}/login with this email.")


def set_active(user, active):
    if user is not None and user.is_active != active:
        user.is_active = active
        user.save(update_fields=["is_active"])
