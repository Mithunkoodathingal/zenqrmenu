from django.db import transaction

from common.email import send_email

from .models import Notification, NotificationPreferences


def prefs_for(restaurant):
    return NotificationPreferences.objects.get_or_create(restaurant=restaurant)[0]


def notify(restaurant, kind, title, message="", order=None):
    """Record an alert for the dashboard bell, and email it too if the owner turned email on for that event."""
    p = prefs_for(restaurant)
    if not p.wants(kind):
        return None
    n = Notification.objects.create(restaurant=restaurant, type=kind, title=title[:150], message=message[:500], order=order)
    if p.email_enabled:
        to = p.email_address or restaurant.email
        transaction.on_commit(lambda: send_email(to, f"{restaurant.name}: {title}", message or title))
    return n
