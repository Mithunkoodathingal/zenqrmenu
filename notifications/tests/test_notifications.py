from django.core import mail
from django.test import TestCase
from rest_framework.test import APIClient

from common.testing import make_menu, owner_client


class NotificationTests(TestCase):
    def setUp(self):
        self.owner, self.r = owner_client()
        self.item, _, self.table = make_menu(self.r)

    def order(self):
        return APIClient().post("/menu/api/orders/", {"table": self.table.id, "items": [{"food_item_id": self.item.id, "quantity": 1}]}, format="json").data

    def test_new_and_changed_orders_ring_the_bell(self):
        o = self.order()
        self.owner.patch(f"/menu/api/orders/{o['id']}/", {"status": "confirmed"}, format="json")
        rows = self.owner.get("/menu/api/notifications/").data
        self.assertEqual([n["type"] for n in rows], ["order_confirmed", "order_received"])
        self.assertFalse(rows[0]["read"])
        self.owner.post(f"/menu/api/notifications/{rows[0]['id']}/read/")
        self.assertTrue(self.owner.get("/menu/api/notifications/").data[0]["read"])
        self.owner.post("/menu/api/notifications/read-all/")
        self.assertTrue(all(n["read"] for n in self.owner.get("/menu/api/notifications/").data))

    def test_preferences_turn_events_off_and_email_on(self):
        p = self.owner.patch("/menu/api/notifications/preferences/", {"email_enabled": True, "email_address": "alerts@malabar.test",
                                                                        "events": {"order_confirmed": False}}, format="json").data
        self.assertEqual((p["email_enabled"], p["events"]["order_confirmed"], p["events"]["order_received"]), (True, False, True))
        with self.captureOnCommitCallbacks(execute=True):
            o = self.order()
        self.assertEqual(mail.outbox[-1].to, ["alerts@malabar.test"])
        self.owner.patch(f"/menu/api/orders/{o['id']}/", {"status": "confirmed"}, format="json")
        self.assertEqual([n["type"] for n in self.owner.get("/menu/api/notifications/").data], ["order_received"])
        self.assertIn("email_address", self.owner.patch("/menu/api/notifications/preferences/", {"email_address": "nope"}, format="json").data)

    def test_test_alert_and_isolation(self):
        self.assertTrue(self.owner.post("/menu/api/notifications/test/", {"channel": "email"}, format="json").data["ok"])
        self.assertEqual(self.owner.post("/menu/api/notifications/test/", {"channel": "whatsapp"}, format="json").status_code, 400)
        self.order()
        other, _ = owner_client("other")
        self.assertEqual(other.get("/menu/api/notifications/").data, [])
