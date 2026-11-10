"""Campaigns only reach diners who agreed to marketing; unsubscribe works without signing in."""
import re

from django.core import mail
from django.test import TestCase
from rest_framework.test import APIClient

from common.testing import make_customer, make_menu, owner_client
from coupons.models import Coupon


class MarketingTests(TestCase):
    def setUp(self):
        self.owner, self.r = owner_client()
        self.item, _, _ = make_menu(self.r)
        self.r.enable_takeaway = True
        self.r.save()
        self.yes, self.p_yes = make_customer("yes@example.com", "Yasmin")
        self.no, self.p_no = make_customer("no@example.com", "Nikhil")
        self.p_yes.set_marketing(True)
        self.p_yes.save()
        for c in (self.yes, self.no):
            c.post("/menu/api/orders/", {"restaurant": self.r.id, "order_type": "pickup", "items": [{"food_item_id": self.item.id, "quantity": 1}]}, format="json")
        make_customer("stranger@example.com", "Sam")[1].set_marketing(True)

    def campaign(self, **extra):
        body = {"name": "Onam", "subject": "Onam sadya is back", "body": "Book your sadya this weekend.", "audience": "all_opted_in", **extra}
        return self.owner.post("/api/marketing/campaigns/", body, format="json")

    def test_customers_list_shows_consent(self):
        rows = {c["email"]: c for c in self.owner.get("/api/marketing/customers/").data}
        self.assertEqual(set(rows), {"yes@example.com", "no@example.com"})  # only diners who ordered here
        self.assertEqual((rows["yes@example.com"]["can_email"], rows["no@example.com"]["can_email"]), (True, False))
        self.assertEqual(rows["yes@example.com"]["orders"], 1)

    def test_send_reaches_only_consenting_customers_with_an_unsubscribe_link(self):
        prev = self.owner.post("/api/marketing/campaigns/preview/", {"audience": "all_opted_in"}, format="json").data
        self.assertEqual((prev["recipients"], prev["skipped"]), (["yes@example.com"], 1))
        cid = self.campaign().data["id"]
        mail.outbox.clear()
        r = self.owner.post(f"/api/marketing/campaigns/{cid}/send/")
        self.assertEqual((r.data["status"], r.data["recipients"], r.data["skipped"]), ("sent", ["yes@example.com"], 1))
        self.assertEqual([m.to for m in mail.outbox], [["yes@example.com"]])
        self.assertEqual(self.owner.post(f"/api/marketing/campaigns/{cid}/send/").status_code, 400)
        self.assertEqual(self.owner.patch(f"/api/marketing/campaigns/{cid}/", {"name": "x"}, format="json").status_code, 400)
        token = re.search(r"/unsubscribe/(\S+)", mail.outbox[0].body).group(1)
        anon = APIClient()
        self.assertFalse(anon.get(f"/api/marketing/unsubscribe/{token}/").data["unsubscribed"])
        self.assertTrue(anon.post(f"/api/marketing/unsubscribe/{token}/", {}, format="json").data["unsubscribed"])
        prev = self.owner.post("/api/marketing/campaigns/preview/", {"audience": "all_opted_in"}, format="json").data
        self.assertEqual(prev["recipients"], [])
        self.assertEqual(self.owner.post(f"/api/marketing/campaigns/{self.campaign().data['id']}/send/").status_code, 400)

    def test_selected_audience_skips_strangers_and_shares_a_personal_coupon(self):
        coupon = Coupon.objects.create(restaurant=self.r, code="ONAM10", discount_type="percent", value=10, audience="selected")
        r = self.campaign(audience="selected", customer_emails=["YES@example.com", "stranger@example.com"], coupon_id=coupon.id)
        self.assertEqual(r.status_code, 201, r.data)
        sent = self.owner.post(f"/api/marketing/campaigns/{r.data['id']}/send/").data
        self.assertEqual(sent["recipients"], ["yes@example.com"])
        coupon.refresh_from_db()
        self.assertEqual(coupon.customer_emails, ["yes@example.com"])
        self.assertIn("ONAM10", mail.outbox[-1].body)

    def test_validation_and_isolation(self):
        self.assertTrue({"name", "body"} <= set(self.campaign(name="", body="short").data))
        self.assertIn("customer_emails", self.campaign(audience="selected").data)
        cid = self.campaign().data["id"]
        other, _ = owner_client("other")
        self.assertEqual(other.post(f"/api/marketing/campaigns/{cid}/send/").status_code, 404)
        self.assertEqual(other.get("/api/marketing/customers/").data, [])
        self.assertEqual(APIClient().get("/api/marketing/unsubscribe/bad-token/").status_code, 404)

    def test_diner_can_withdraw_consent(self):
        r = self.yes.post("/api/marketing/consent/", {"marketing_opt_in": False}, format="json")
        self.assertFalse(r.data["marketing_opt_in"])
        self.assertEqual(self.owner.post("/api/marketing/campaigns/preview/", {"audience": "all_opted_in"}, format="json").data["recipients"], [])
