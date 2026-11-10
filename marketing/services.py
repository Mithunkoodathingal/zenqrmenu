from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Max, Q, Sum
from django.utils import timezone

from customers.models import CustomerProfile

RECENT_DAYS = 30


def can_email(p):
    return p.marketing_opt_in and p.unsubscribed_at is None


def restaurant_customers(restaurant):
    """Diners with an account who have ordered here, with their order count and spend."""
    live = Q(orders__restaurant=restaurant) & ~Q(orders__status="cancelled")
    return (CustomerProfile.objects.filter(orders__restaurant=restaurant).distinct()
            .annotate(n=Count("orders", filter=live, distinct=True), spend=Sum("orders__total", filter=live),
                      last=Max("orders__created_at", filter=Q(orders__restaurant=restaurant))))


def audience(restaurant, kind, emails):
    """(recipient profiles, skipped [{email, reason}])."""
    customers = list(restaurant_customers(restaurant))
    skipped = []
    if kind == "selected":
        wanted = {str(e).strip().lower() for e in emails or [] if str(e).strip()}
        by_email = {c.email.lower(): c for c in customers}
        pool = []
        for e in sorted(wanted):
            if e in by_email:
                pool.append(by_email[e])
            else:
                skipped.append({"email": e, "reason": "not a customer"})
    elif kind == "recent":
        since = timezone.now() - timedelta(days=RECENT_DAYS)
        pool = [c for c in customers if c.last and c.last >= since]
    else:
        pool = customers
    out = []
    for c in pool:
        if can_email(c):
            out.append(c)
        else:
            skipped.append({"email": c.email, "reason": "unsubscribed" if c.unsubscribed_at else "no consent"})
    return out, skipped


def unsubscribe_url(profile):
    return f"{settings.FRONTEND_URL}/unsubscribe/{profile.unsubscribe_token}"
