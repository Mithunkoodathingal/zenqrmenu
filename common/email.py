import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

log = logging.getLogger(__name__)


def send_email(to, subject, text, html=None):
    """Send one email. Failures are logged, never raised, so a mail outage can't break checkout or sign-up."""
    if not to:
        return False
    recipients = [to] if isinstance(to, str) else list(to)
    try:
        message = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, recipients)
        if html:
            message.attach_alternative(html, "text/html")
        message.send()
        return True
    except Exception:  # pragma: no cover - depends on the mail provider
        log.exception("Email to %s failed: %s", recipients, subject)
        return False
