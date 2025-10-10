# restaurant/signals.py
import logging
from django.dispatch import receiver
from allauth.account.signals import email_confirmed
from allauth.account.models import EmailAddress

logger = logging.getLogger(__name__)

@receiver(email_confirmed)
def handle_email_confirmed(request, email_address: EmailAddress, **kwargs):
    """
    When a user confirms their email via allauth, ensure the EmailAddress
    is verified and activate the associated user.
    """
    try:
        user = email_address.user
        # Ensure EmailAddress is marked verified
        if not email_address.verified:
            email_address.verified = True
            email_address.save(update_fields=['verified'])
        # Activate the user
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])
            logger.info("Activated user id=%s (%s) after email confirmation.", user.id, user.email)
    except Exception as exc:
        logger.exception(
            "Error activating user on email_confirmed for email %s: %s",
            getattr(email_address, 'email', None),
            exc
        )
