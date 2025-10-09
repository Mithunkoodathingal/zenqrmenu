# restaurant/signals.py
from django.dispatch import receiver
from allauth.account.signals import email_confirmed
from allauth.account.models import EmailAddress
import logging

logger = logging.getLogger(__name__)

@receiver(email_confirmed)
def handle_email_confirmed(request, email_address: EmailAddress, **kwargs):
    user = email_address.user
    if not email_address.verified:
        email_address.verified = True
        email_address.save(update_fields=['verified'])
    if not user.is_active:
        user.is_active = True
        user.save(update_fields=['is_active'])
        logger.info("Activated user id=%s after confirmation", user.id)
