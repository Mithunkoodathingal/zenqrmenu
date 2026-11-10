from django.conf import settings
from django.db import models


class OwnerAccount(models.Model):
    """Restaurant-owner sign-up details. Owners must confirm their email before logging in."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owner_account")
    email_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    google_sub = models.CharField(max_length=64, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username
