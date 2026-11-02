"""Tests for the coupon + review additions used by the Lovable frontend."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from restaurant.feature_models import Coupon, Review
from restaurant.models import Restaurant

User = get_user_model()


def make_restaurant(username):
    user = User.objects.create_user(username=username, email=f"{username}@x.com", password="pw12345!")
    r = Restaurant.objects.create(owner=user, name=f"R {username}", address="Somewhere")
    return user, r


class CouponTests(TestCase):
    def setUp(self):
        self.user, self.r = make_restaurant("owner1")
        self.c = APIClient()
        self.c.force_authenticate(self.user)

    def test_create_saves_new_fields(self):
        res = self.c.post("/api/coupons/", {
            "code": "bogo1", "discount_type": "bogo", "value": 0,
            "description": "Free second pizza", "per_user_limit": 2,
            "applicable_days": [1, 2, 3],
        }, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        coupon = res.json()["coupon"]
        self.assertEqual(coupon["code"], "BOGO1")
        self.assertEqual(coupon["discount_type"], "bogo")
        self.assertEqual(coupon["per_user_limit"], 2)
        self.assertEqual(coupon["applicable_days"], [1, 2, 3])
        self.assertEqual(coupon["description"], "Free second pizza")

    def test_all_seven_days_stored_as_every_day(self):
        res = self.c.post("/api/coupons/", {"code": "ALL", "value": 10, "applicable_days": [0, 1, 2, 3, 4, 5, 6]}, format="json")
        self.assertEqual(res.json()["coupon"]["applicable_days"], [])

    def test_bogo_validate_makes_cheapest_half_free(self):
        Coupon.objects.create(restaurant=self.r, code="BOGO", discount_type="bogo", value=0)
        res = APIClient().post(f"/api/restaurants/{self.r.id}/coupons/validate/", {
            "code": "bogo", "order_amount": "500",
            "items": [{"price": "200", "quantity": 2}, {"price": "100", "quantity": 1}],
        }, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        # Units 100, 200, 200 -> one free unit, the cheapest (100).
        self.assertEqual(Decimal(str(res.json()["discount_amount"])), Decimal("100.00"))

    def test_bogo_without_items_is_rejected(self):
        Coupon.objects.create(restaurant=self.r, code="BOGO", discount_type="bogo", value=0)
        res = APIClient().post(f"/api/restaurants/{self.r.id}/coupons/validate/", {"code": "BOGO", "order_amount": "500"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_wrong_day_is_rejected(self):
        today = (timezone.localtime().weekday() + 1) % 7
        Coupon.objects.create(restaurant=self.r, code="DAY", value=10, applicable_days=[(today + 1) % 7])
        res = APIClient().post(f"/api/restaurants/{self.r.id}/coupons/validate/", {"code": "DAY", "order_amount": "500"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("not valid today", res.json()["message"])

    def test_per_user_limit_needs_customer_identity(self):
        Coupon.objects.create(restaurant=self.r, code="ONCE", value=10, per_user_limit=1)
        res = APIClient().post(f"/api/restaurants/{self.r.id}/coupons/validate/", {"code": "ONCE", "order_amount": "500"}, format="json")
        self.assertEqual(res.status_code, 400)
        res = APIClient().post(f"/api/restaurants/{self.r.id}/coupons/validate/", {"code": "ONCE", "order_amount": "500", "customer_phone": "999"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)

    def test_other_owner_cannot_edit_coupon(self):
        coupon = Coupon.objects.create(restaurant=self.r, code="MINE", value=10)
        other, _ = make_restaurant("owner2")
        c2 = APIClient(); c2.force_authenticate(other)
        self.assertEqual(c2.patch(f"/api/coupons/{coupon.id}/", {"value": 99}, format="json").status_code, 404)


class OwnerReviewListTests(TestCase):
    def setUp(self):
        self.user, self.r = make_restaurant("owner3")
        Review.objects.create(restaurant=self.r, customer_name="A", rating=5, is_published=True)
        Review.objects.create(restaurant=self.r, customer_name="B", rating=1, is_published=False)
        self.c = APIClient(); self.c.force_authenticate(self.user)

    def test_owner_sees_hidden_reviews(self):
        res = self.c.get("/api/reviews/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["count"], 2)

    def test_status_filter(self):
        self.assertEqual(self.c.get("/api/reviews/?status=hidden").json()["count"], 1)
        self.assertEqual(self.c.get("/api/reviews/?status=published").json()["count"], 1)

    def test_public_list_still_only_published(self):
        res = APIClient().get(f"/api/restaurants/{self.r.id}/reviews/")
        self.assertEqual(res.json()["count"], 1)

    def test_requires_login(self):
        self.assertIn(APIClient().get("/api/reviews/").status_code, (401, 403))

    def test_other_owner_sees_none_of_mine(self):
        other, _ = make_restaurant("owner4")
        c2 = APIClient(); c2.force_authenticate(other)
        self.assertEqual(c2.get("/api/reviews/").json()["count"], 0)
