from django.db.models import Avg, Count

from .models import Review


def eligibility(order, profile):
    """(eligible, reason, existing review)."""
    existing = Review.objects.filter(order=order).first()
    if not profile.email_verified:
        return False, "Verify your email to review.", existing
    if order.customer_id != profile.id:
        return False, "This order isn't in your account.", existing
    if order.status != "completed":
        return False, "You can review once the order is completed.", existing
    if existing:
        return False, "You've already reviewed this order.", existing
    return True, "", None


def review_state(order):
    """(can_review, reviewed) for the diner's order list."""
    reviewed = Review.objects.filter(order=order).exists()
    return order.status == "completed" and order.customer_id is not None and not reviewed, reviewed


def public_reviews(restaurant):
    return Review.objects.filter(restaurant=restaurant, is_published=True, removed_by_admin=False)


def summary(qs):
    s = qs.aggregate(avg=Avg("rating"), n=Count("id"))
    return round(float(s["avg"] or 0), 1), s["n"]


def rating_summary(restaurant):
    """(average rating or None, number of reviews) for restaurant cards and profiles."""
    avg, n = summary(public_reviews(restaurant))
    return (avg if n else None), n
