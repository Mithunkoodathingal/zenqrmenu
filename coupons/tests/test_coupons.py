from rest_framework.test import APIClient

from coupons.models import Coupon
from orders.tests.test_orders import OrderTestBase


class CouponTests(OrderTestBase):
    def coupon(self, **f):
        base = {"restaurant": self.r, "code": "SAVE10", "discount_type": "percent", "value": 10}
        base.update(f)
        return Coupon.objects.create(**base)

    def validate(self, client, code, amount, items=None):
        return client.post(f"/api/restaurants/{self.r.id}/coupons/validate/",
                           {"code": code, "order_amount": amount, "items": items or []}, format="json")

    def test_percent_coupon_is_capped_by_maximum_discount(self):
        self.coupon(maximum_discount=50)
        self.assertEqual(self.validate(self.diner, "save10", 600).data["discount_amount"], 50.0)
        self.assertEqual(self.validate(self.diner, "SAVE10", 300).data["discount_amount"], 30.0)

    def test_guests_cannot_use_coupons(self):
        self.coupon()
        self.assertEqual(self.validate(APIClient(), "SAVE10", 600).status_code, 400)
        r = self.dinein(coupon_code="SAVE10")
        self.assertEqual(r.status_code, 400)

    def test_minimum_order_message_says_how_much_more(self):
        self.coupon(minimum_order_amount=500)
        r = self.validate(self.diner, "SAVE10", 420)
        self.assertEqual(r.status_code, 400)
        self.assertIn("Add ₹80 more", r.data["message"])

    def test_buy_one_get_one_takes_off_the_cheapest_item(self):
        self.coupon(code="BOGO", discount_type="bogo", value=0)
        r = self.validate(self.diner, "BOGO", 350, [{"price": 200, "quantity": 1}, {"price": 150, "quantity": 1}])
        self.assertEqual(r.data["discount_amount"], 150.0)

    def test_per_diner_limit_and_cancel_gives_the_use_back(self):
        c = self.coupon(per_user_limit=1)
        first = self.pickup(coupon_code="SAVE10")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(first.data["discount_amount"], 20.0)
        self.assertEqual(first.data["total_price"], 180.0)
        self.assertEqual(self.pickup(coupon_code="SAVE10").status_code, 400)
        self.owner.patch(f"/menu/api/orders/{first.data['id']}/", {"status": "cancelled"}, format="json")
        c.refresh_from_db()
        self.assertEqual(c.used_count, 0)
        self.assertEqual(self.pickup(coupon_code="SAVE10").status_code, 201)

    def test_selected_customer_offer_is_only_for_listed_emails(self):
        self.coupon(code="VIP", audience="selected", customer_emails=["diner@example.com"])
        self.coupon(code="ALL", audience="everyone")
        guest = APIClient().get(f"/api/public/restaurants/{self.r.id}/offers/").data
        self.assertEqual([o["code"] for o in guest["offers"]], ["ALL"])
        self.assertEqual(guest["locked_count"], 1)
        mine = self.diner.get(f"/api/public/restaurants/{self.r.id}/offers/").data
        self.assertEqual(sorted(o["code"] for o in mine["offers"]), ["ALL", "VIP"])
        from common.testing import make_customer
        other, _ = make_customer("other@example.com")
        self.assertEqual(self.validate(other, "VIP", 600).status_code, 400)

    def test_owner_creates_coupon_in_website_shape_and_delete_switches_it_off(self):
        r = self.owner.post("/api/coupons/", {"code": "monsoon", "discount_type": "fixed", "value": 75, "applicable_days": [0, 6]}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["coupon"]["code"], "MONSOON")
        cid = r.data["coupon"]["id"]
        self.assertEqual(self.owner.post("/api/coupons/", {"code": "MONSOON", "discount_type": "fixed", "value": 5}, format="json").status_code, 400)
        self.owner.delete(f"/api/coupons/{cid}/")
        self.assertFalse(Coupon.objects.get(pk=cid).is_active)
