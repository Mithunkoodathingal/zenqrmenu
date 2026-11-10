import re
from datetime import timedelta
from decimal import Decimal

from django.core import mail
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from common.testing import make_customer, make_menu, owner_client
from menu.models import BranchItemOverride
from orders.models import Order
from restaurants.models import Branch, Table


class OrderTestBase(TestCase):
    def setUp(self):
        self.owner, self.r = owner_client()
        self.item, self.addon, self.table = make_menu(self.r)
        self.guest = APIClient()
        self.diner, self.profile = make_customer()

    def dinein(self, client=None, **extra):
        body = {"table": self.table.id, "items": [{"food_item_id": self.item.id, "quantity": 2, "selected_addons_ids": [self.addon.id]}]}
        body.update(extra)
        return (client or self.guest).post("/menu/api/orders/", body, format="json")

    def pickup(self, client=None, **extra):
        body = {"restaurant": self.r.id, "order_type": "pickup", "items": [{"food_item_id": self.item.id, "quantity": 1}]}
        body.update(extra)
        return (client or self.diner).post("/menu/api/orders/", body, format="json")


class PlacingOrdersTests(OrderTestBase):
    def test_server_prices_the_order_and_ignores_client_totals(self):
        r = self.dinein(total_price=1)
        self.assertEqual(r.status_code, 201, r.data)
        # 2 × (₹200 biryani + ₹30 raita)
        self.assertEqual(r.data["subtotal"], 460.0)
        self.assertEqual(r.data["total_price"], 460.0)
        self.assertEqual(r.data["order_number"], "ZQ-1001")
        self.assertEqual(r.data["table_number"], "1")

    def test_guests_can_only_order_dine_in(self):
        r = self.pickup(client=self.guest)
        self.assertEqual(r.status_code, 401)
        self.assertIn("Sign in", r.data["message"])

    def test_branch_price_override_is_charged_at_that_branch(self):
        b2 = Branch.objects.create(restaurant=self.r, name="Beach")
        t2 = Table.objects.create(restaurant=self.r, branch=b2, table_number="B1")
        BranchItemOverride.objects.create(branch=b2, food_item=self.item, price="180.00")
        r = self.guest.post("/menu/api/orders/", {"table": t2.id, "items": [{"food_item_id": self.item.id, "quantity": 1}]}, format="json")
        self.assertEqual(r.data["total_price"], 180.0)
        self.assertEqual(r.data["branch_name"], "Beach")

    def test_paused_item_is_refused(self):
        self.item.is_available = False
        self.item.save()
        r = self.dinein()
        self.assertEqual(r.status_code, 400)
        self.assertIn("Paused by restaurant", r.data["message"])

    def test_closed_restaurant_refuses_asap_pickup_but_takes_a_scheduled_one(self):
        hours = {d: {"is_open": False, "open": "09:00", "close": "22:00"} for d in
                 ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}
        tomorrow = (timezone.now() + timedelta(days=1)).astimezone(timezone.get_default_timezone())
        day = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][tomorrow.weekday()]
        hours[day] = {"is_open": True, "open": "09:00", "close": "22:00"}
        self.r.working_hours = {**hours, "holidays": []}
        self.r.save()
        self.assertEqual(self.pickup().status_code, 400)
        when = tomorrow.replace(hour=12, minute=0, second=0, microsecond=0)
        r = self.pickup(scheduled_time=when.isoformat())
        self.assertEqual(r.status_code, 201, r.data)

    def test_pickup_tip_goes_to_restaurant_and_is_added(self):
        r = self.pickup(tip_amount=20, utensils_needed=True)
        self.assertEqual(r.data["total_price"], 220.0)
        self.assertEqual(r.data["tip_recipient"], "restaurant")
        self.assertTrue(r.data["utensils_needed"])

    def test_delivery_charge_is_per_km_beyond_the_free_distance(self):
        self.r.enable_delivery, self.r.max_delivery_km, self.r.free_delivery_km, self.r.charge_per_extra_km = True, 10, 1, 10
        self.r.save()
        # ~3.34 km north of the restaurant → 2.34 km charged at ₹10
        r = self.diner.post("/menu/api/orders/", {"restaurant": self.r.id, "order_type": "delivery", "customer_address": "Beach Rd",
                                                  "delivery_latitude": 11.2888, "delivery_longitude": 75.7804, "tip_amount": 30,
                                                  "items": [{"food_item_id": self.item.id, "quantity": 1}]}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertAlmostEqual(r.data["delivery_charge"], 23.4, places=1)
        self.assertEqual(r.data["tip_recipient"], "driver")
        self.assertAlmostEqual(r.data["total_price"], 200 + 23.4 + 30, places=1)

    def test_delivery_outside_the_area_is_refused(self):
        self.r.enable_delivery, self.r.max_delivery_km = True, 2
        self.r.save()
        r = self.diner.post("/menu/api/orders/", {"restaurant": self.r.id, "order_type": "delivery", "customer_address": "Far",
                                                  "delivery_latitude": 11.40, "delivery_longitude": 75.78,
                                                  "items": [{"food_item_id": self.item.id, "quantity": 1}]}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("outside", r.data["message"])


class StatusTests(OrderTestBase):
    def test_completed_orders_cannot_go_back(self):
        oid = self.dinein().data["id"]
        self.assertEqual(self.owner.patch(f"/menu/api/orders/{oid}/", {"status": "completed"}, format="json").status_code, 200)
        r = self.owner.patch(f"/menu/api/orders/{oid}/", {"status": "preparing"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_completing_a_cash_order_records_payment_and_receipt(self):
        oid = self.dinein().data["id"]
        self.owner.patch(f"/menu/api/orders/{oid}/", {"status": "completed"}, format="json")
        o = Order.objects.get(pk=oid)
        self.assertEqual(o.payment_status, "paid")
        self.assertEqual(o.payments.get().amount, Decimal("460.00"))
        self.assertTrue(o.receipt.invoice_number.startswith("INV-"))

    def test_other_restaurants_cannot_see_the_order(self):
        oid = self.dinein().data["id"]
        other, _ = owner_client("rival")
        self.assertEqual(other.get(f"/menu/api/orders/{oid}/").status_code, 404)

    def test_tracking_page_hides_contact_details_from_strangers(self):
        oid = self.pickup(customer_phone="9811111111").data["id"]
        stranger = APIClient().get(f"/menu/api/orders/{oid}/public/").data
        self.assertNotIn("customer_phone", stranger)
        mine = self.diner.get(f"/menu/api/orders/{oid}/public/").data
        self.assertEqual(mine["customer_phone"], "9811111111")

    def test_diner_sees_order_in_history(self):
        self.pickup()
        rows = self.diner.get("/api/customers/me/orders/").data
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["restaurant_name"], "Malabar Kitchen")


class HandoverCodeTests(OrderTestBase):
    def test_ready_pickup_emails_a_code_that_completes_the_order(self):
        oid = self.pickup().data["id"]
        with self.captureOnCommitCallbacks(execute=True):
            self.owner.patch(f"/menu/api/orders/{oid}/", {"status": "ready"}, format="json")
        code = re.search(r": (\d{4})\b", mail.outbox[-1].body).group(1)
        self.assertEqual(self.owner.post(f"/payments/orders/{oid}/complete/").status_code, 400)
        wrong = "0000" if code != "0000" else "1111"
        self.assertEqual(self.owner.post(f"/payments/orders/{oid}/verify-otp/", {"otp": wrong}, format="json").status_code, 400)
        self.assertTrue(self.owner.post(f"/payments/orders/{oid}/verify-otp/", {"otp": code}, format="json").data["verified"])
        self.assertEqual(self.owner.post(f"/payments/orders/{oid}/complete/").status_code, 200)
        self.assertEqual(Order.objects.get(pk=oid).status, "completed")
