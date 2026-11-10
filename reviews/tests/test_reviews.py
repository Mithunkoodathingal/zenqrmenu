"""Review rules the user set: verified diners, one per completed order, edit 7 days, delete any time, owners hide only."""
from datetime import timedelta

from django.test import TestCase
from rest_framework.test import APIClient

from common.testing import make_customer, make_menu, owner_client
from orders.models import Order
from reviews.models import Review


class ReviewTests(TestCase):
    def setUp(self):
        self.owner, self.r = owner_client()
        self.item, _, _ = make_menu(self.r)
        self.r.enable_takeaway = True
        self.r.save()
        self.diner, self.profile = make_customer()
        self.order = self.place()

    def place(self, client=None):
        r = (client or self.diner).post("/menu/api/orders/", {"restaurant": self.r.id, "order_type": "pickup",
                                                              "items": [{"food_item_id": self.item.id, "quantity": 1}]}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def complete(self, o):
        self.owner.patch(f"/menu/api/orders/{o['id']}/", {"status": "completed"}, format="json")

    def review(self, o, rating=5, client=None):
        return (client or self.diner).post(f"/api/customers/me/orders/{o['id']}/review/", {"rating": rating, "comment": "Lovely biryani"}, format="json")

    def test_only_completed_orders_can_be_reviewed_once(self):
        self.assertFalse(self.diner.get(f"/api/customers/me/orders/{self.order['id']}/review-eligibility/").data["eligible"])
        self.assertEqual(self.review(self.order).status_code, 400)
        self.complete(self.order)
        self.assertTrue(self.diner.get(f"/api/customers/me/orders/{self.order['id']}/review-eligibility/").data["eligible"])
        self.assertEqual(self.review(self.order).status_code, 201)
        self.assertEqual(self.review(self.order).status_code, 400)
        e = self.diner.get(f"/api/customers/me/orders/{self.order['id']}/review-eligibility/").data
        self.assertIsNotNone(e["existing_review_id"])
        pub = APIClient().get(f"/api/restaurants/{self.r.id}/reviews/").data
        self.assertEqual((pub["count"], pub["average_rating"], pub["reviews"][0]["customer_name"]), (1, 5.0, "Asha"))
        self.assertTrue(self.diner.get("/api/customers/me/orders/").data[0]["reviewed"])

    def test_unverified_diners_and_strangers_cannot_review(self):
        self.complete(self.order)
        self.profile.email_verified = False
        self.profile.save()
        self.assertEqual(self.review(self.order).status_code, 400)
        other, _ = make_customer("other@example.com", "Bilal")
        self.assertEqual(self.review(self.order, client=other).status_code, 404)
        self.assertEqual(APIClient().post(f"/api/customers/me/orders/{self.order['id']}/review/", {"rating": 5}).status_code, 401)

    def test_bad_rating_is_refused(self):
        self.complete(self.order)
        self.assertIn("rating", self.review(self.order, rating=6).data)
        self.assertIn("rating", self.review(self.order, rating=0).data)

    def test_diner_edits_for_seven_days_and_deletes_any_time(self):
        self.complete(self.order)
        rid = self.review(self.order).data["id"]
        r = self.diner.patch(f"/api/customers/me/reviews/{rid}/", {"rating": 3}, format="json")
        self.assertEqual(r.data["rating"], 3)
        Review.objects.filter(pk=rid).update(created_at=Review.objects.get(pk=rid).created_at - timedelta(days=8))
        self.assertEqual(self.diner.patch(f"/api/customers/me/reviews/{rid}/", {"rating": 1}, format="json").status_code, 400)
        self.assertEqual(self.diner.delete(f"/api/customers/me/reviews/{rid}/").status_code, 204)

    def test_owner_replies_and_hides_but_cannot_delete_or_rewrite(self):
        self.complete(self.order)
        rid = self.review(self.order).data["id"]
        r = self.owner.patch(f"/api/reviews/{rid}/", {"owner_response": "Thank you!"}, format="json")
        self.assertEqual(r.data["review"]["owner_response"], "Thank you!")
        self.owner.patch(f"/api/reviews/{rid}/", {"is_published": False}, format="json")
        self.assertEqual(APIClient().get(f"/api/restaurants/{self.r.id}/reviews/").data["count"], 0)
        self.assertEqual(len(self.owner.get("/api/reviews/", {"status": "hidden"}).data["reviews"]), 1)
        self.assertEqual(self.owner.delete(f"/api/reviews/{rid}/").status_code, 403)
        self.assertEqual(self.owner.patch(f"/api/reviews/{rid}/", {"rating": 1}, format="json").status_code, 400)
        other, _ = owner_client("other")
        self.assertEqual(other.patch(f"/api/reviews/{rid}/", {"is_published": True}, format="json").status_code, 404)

    def test_admin_removed_reviews_disappear_everywhere(self):
        self.complete(self.order)
        rid = self.review(self.order).data["id"]
        Review.objects.filter(pk=rid).update(removed_by_admin=True)
        self.assertEqual(APIClient().get(f"/api/restaurants/{self.r.id}/reviews/").data["count"], 0)
        self.assertEqual(self.owner.get("/api/reviews/").data["reviews"], [])
        self.assertEqual(Order.objects.count(), 1)
