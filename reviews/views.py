from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from common.permissions import IsOwnerOrRole
from common.tenancy import get_restaurant
from customers.views import IsCustomer
from orders.models import Order
from restaurants.models import Restaurant

from .models import Review
from .services import eligibility, public_reviews, summary


def review_out(r, owner=False):
    out = {"id": r.id, "customer_name": r.customer_name, "rating": r.rating, "comment": r.comment,
           "owner_response": r.owner_response, "created_at": r.created_at, "edited_at": r.edited_at}
    if owner:
        out.update({"is_published": r.is_published, "order_id": r.order_id, "order_number": r.order.order_number})
    return out


def mine_out(r):
    return {**review_out(r), "order_id": r.order_id, "restaurant_id": r.restaurant_id, "restaurant_name": r.restaurant.name,
            "editable": r.editable, "editable_until": r.editable_until,
            "is_published": r.is_published and not r.removed_by_admin}


def _rating(d, required):
    if "rating" not in d and not required:
        return None
    try:
        v = int(d.get("rating"))
    except (TypeError, ValueError):
        v = 0
    if not 1 <= v <= 5 or str(d.get("rating")).strip() not in {str(v), f"{v}.0"}:
        raise ValidationError({"rating": ["Pick 1 to 5 stars."]})
    return v


def _comment(d):
    c = str(d.get("comment") or "").strip()
    if len(c) > 1000:
        raise ValidationError({"comment": ["Keep it under 1000 characters."]})
    return c


@api_view(["GET"])
@permission_classes([AllowAny])
def restaurant_reviews(request, pk):
    r = get_object_or_404(Restaurant, pk=pk, is_active=True)
    qs = public_reviews(r)
    avg, n = summary(qs)
    return Response({"count": n, "average_rating": avg, "reviews": [review_out(x) for x in qs[:100]]})


@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def owner_reviews(request):
    r = get_restaurant(request, required=False)
    if r is None:
        return Response({"reviews": [], "average_rating": 0, "total_reviews": 0})
    qs = Review.objects.filter(restaurant=r, removed_by_admin=False).select_related("order")
    avg, n = summary(qs.filter(is_published=True))
    status = request.query_params.get("status")
    if status in ("published", "hidden"):
        qs = qs.filter(is_published=status == "published")
    return Response({"reviews": [review_out(x, True) for x in qs[:300]], "average_rating": avg, "total_reviews": n})


owner_reviews.cls.allowed_roles = ["manager"]


@api_view(["PATCH", "DELETE"])
@permission_classes([IsOwnerOrRole])
def owner_review(request, pk):
    rv = get_object_or_404(Review.objects.select_related("order"), pk=pk, restaurant=get_restaurant(request), removed_by_admin=False)
    if request.method == "DELETE":
        raise PermissionDenied("Restaurants can hide a review but not delete it.")
    d = request.data
    if set(d) & {"rating", "comment", "customer_name"}:
        raise ValidationError({"detail": "Only the diner can change their review."})
    if "owner_response" in d:
        text = str(d.get("owner_response") or "").strip()
        if len(text) > 1000:
            raise ValidationError({"owner_response": ["Keep it under 1000 characters."]})
        rv.owner_response, rv.owner_responded_at = text, timezone.now() if text else None
    if "is_published" in d:
        rv.is_published = str(d.get("is_published")).lower() in {"true", "1"}
    rv.save()
    return Response({"review": review_out(rv, True)})


owner_review.cls.allowed_roles = ["manager"]


def _my_order(request, pk):
    return get_object_or_404(Order, pk=pk, customer=request.user.customer_profile)


@api_view(["GET"])
@permission_classes([IsCustomer])
def review_eligibility(request, pk):
    o = _my_order(request, pk)
    ok, reason, existing = eligibility(o, request.user.customer_profile)
    return Response({"eligible": ok, "reason": reason or None, "existing_review_id": existing.id if existing else None,
                     "editable_until": existing.editable_until if existing and existing.editable else None})


@api_view(["POST"])
@permission_classes([IsCustomer])
def write_review(request, pk):
    profile = request.user.customer_profile
    o = _my_order(request, pk)
    ok, reason, _ = eligibility(o, profile)
    if not ok:
        raise ValidationError({"detail": reason})
    rv = Review.objects.create(restaurant=o.restaurant, order=o, customer=profile, rating=_rating(request.data, True),
                               comment=_comment(request.data), customer_name=(profile.name or "Diner")[:120])
    return Response(mine_out(rv), status=201)


@api_view(["GET"])
@permission_classes([IsCustomer])
def my_reviews(request):
    qs = request.user.customer_profile.reviews.select_related("restaurant")
    return Response([mine_out(r) for r in qs])


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsCustomer])
def my_review(request, pk):
    rv = get_object_or_404(Review.objects.select_related("restaurant"), pk=pk, customer=request.user.customer_profile)
    if request.method == "DELETE":
        rv.delete()  # diners may delete any time
        return Response(status=204)
    if request.method == "PATCH":
        if not rv.editable:
            raise ValidationError({"detail": "Reviews can only be edited for 7 days."})
        rating = _rating(request.data, False)
        if rating is not None:
            rv.rating = rating
        if "comment" in request.data:
            rv.comment = _comment(request.data)
        rv.edited_at = timezone.now()
        rv.save()
    return Response(mine_out(rv))
