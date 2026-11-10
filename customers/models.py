"""Diner accounts: a normal User with a CustomerProfile. Diners sign in with a code sent to their email."""
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


def _token():
    return secrets.token_urlsafe(24)


class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer_profile")
    name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    email_verified = models.BooleanField(default=False)
    photo = models.ImageField(upload_to="customers/photos/", blank=True, null=True)
    marketing_opt_in = models.BooleanField(default=False)
    marketing_consent_at = models.DateTimeField(null=True, blank=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    unsubscribe_token = models.CharField(max_length=64, unique=True, default=_token)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or self.email

    def set_marketing(self, opt_in):
        """Turning consent on records when it was given; turning it off clears it."""
        opt_in = bool(opt_in)
        if opt_in and not self.marketing_opt_in:
            self.marketing_consent_at = timezone.now()
            self.unsubscribed_at = None
        if not opt_in:
            self.marketing_consent_at = None
        self.marketing_opt_in = opt_in


class EmailCode(models.Model):
    """One-time sign-in code. Only a hash is stored; codes expire and lock after too many wrong tries."""

    VALID_MINUTES = 10
    MAX_ATTEMPTS = 5

    email = models.EmailField(db_index=True)
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)

    @staticmethod
    def hash(code):
        return hashlib.sha256(f"{settings.SECRET_KEY}:{code}".encode()).hexdigest()

    @classmethod
    def issue(cls, email):
        code = f"{secrets.randbelow(1_000_000):06d}"
        cls.objects.filter(email=email, used_at__isnull=True).update(used_at=timezone.now())
        cls.objects.create(email=email, code_hash=cls.hash(code), expires_at=timezone.now() + timedelta(minutes=cls.VALID_MINUTES))
        return code

    def usable(self):
        return self.used_at is None and self.attempts < self.MAX_ATTEMPTS and timezone.now() < self.expires_at


class CustomerAddress(models.Model):
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=40, default="Home")
    recipient_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    house = models.CharField(max_length=200)
    street = models.CharField(max_length=200, blank=True)
    area = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=12, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "-updated_at"]
        constraints = [models.UniqueConstraint(fields=["customer"], condition=models.Q(is_default=True), name="one_default_address")]

    def one_line(self):
        return ", ".join(p for p in [self.house, self.street, self.area, self.city, self.state, self.postal_code] if p)
