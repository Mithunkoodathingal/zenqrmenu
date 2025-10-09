# restaurant/signals.py
import logging
from django.dispatch import receiver
from allauth.account.signals import email_confirmed
from allauth.account.models import EmailAddress

logger = logging.getLogger(__name__)

@receiver(email_confirmed)
def handle_email_confirmed(request, email_address: EmailAddress, **kwargs):
    """
    When a user confirms an email via allauth, ensure the user is active
    and the EmailAddress is marked verified.
    """
    try:
        user = email_address.user
        # mark the EmailAddress verified (allauth normally does this)
        if not email_address.verified:
            email_address.verified = True
            email_address.save(update_fields=['verified'])
        # activate user so they can login
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])
            logger.info("Activated user id=%s (%s) after email confirmation.", user.id, user.email)
    except Exception as exc:
        logger.exception("Error in email_confirmed handler for email=%s: %s", getattr(email_address, 'email', None), exc)
