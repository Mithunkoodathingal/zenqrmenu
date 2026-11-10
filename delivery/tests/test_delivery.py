"""Riders: adding them, assignment rules, the rider's own trip screens, and what the diner's tracking page shows."""
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from common.testing import make_customer, make_menu, owner_client
from payments.models import Payment
from staff.tests.test_staff import PNG, staff_login


class DeliveryTests(TestCase):
    def setUp(self):
        self.owner, self.r = owner_client()
        self.item, _, self.table = make_menu(self.r)
        self.r.enable_delivery, self.r.max_delivery_km = True, 10
        self.r.save()
        self.diner, _ = make_customer()
        photo = SimpleUploadedFile("rider.png", PNG, content_type="image/png")
        r = self.owner.post("/api/delivery-partners/", {"first_name": "Faisal", "phone": "9847011111", "vehicle_type": "scooter",
                                                        "vehicle_number": "kl11ab1234", "email": "faisal@riders.test",
                                                        "profile_photo": photo}, format="multipart")
        self.assertEqual(r.status_code, 201, r.data)
        self.rider = r.data["delivery_partner"]

    def delivery_order(self):
        r = self.diner.post("/menu/api/orders/", {"restaurant": self.r.id, "order_type": "delivery", "customer_address": "Beach Rd",
                                                  "customer_phone": "9800000001", "delivery_latitude": 11.2888, "delivery_longitude": 75.7804,
                                                  "items": [{"food_item_id": self.item.id, "quantity": 1}]}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def assign(self, order, rider=None):
        return self.owner.post(f"/api/orders/{order['id']}/assign-partner/", {"delivery_partner": (rider or self.rider)["id"]}, format="json")

    def set(self, order, status):
        r = self.owner.patch(f"/menu/api/orders/{order['id']}/", {"status": status}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        return r.data

    def test_rider_details_and_photo(self):
        self.assertEqual((self.rider["vehicle_number"], self.rider["is_available"]), ("KL11AB1234", True))
        self.assertTrue(self.rider["profile_photo"].startswith("http"))
        r = self.owner.post("/api/delivery-partners/", {"first_name": "Ann", "phone": "9847011111"}, format="json")
        self.assertIn("phone", r.data)
        self.assertEqual(len(self.owner.get("/api/delivery-partners/").data["delivery_partners"]), 1)

    def test_only_open_delivery_orders_get_a_free_rider(self):
        dinein = APIClient().post("/menu/api/orders/", {"table": self.table.id, "items": [{"food_item_id": self.item.id, "quantity": 1}]}, format="json").data
        self.assertEqual(self.assign(dinein).status_code, 400)
        o = self.delivery_order()
        r = self.assign(o)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["order"]["delivery_partner"]["name"], "Faisal")
        rider = self.owner.get(f"/api/delivery-partners/{self.rider['id']}/").data["delivery_partner"]
        self.assertEqual((rider["is_available"], rider["active_orders"]), (False, [o["order_number"]]))
        self.assertEqual(self.assign(self.delivery_order()).status_code, 400)  # busy rider
        self.assertEqual(self.assign(o).status_code, 400)  # already has a rider
        self.owner.post(f"/api/orders/{o['id']}/unassign-partner/")
        self.assertTrue(self.owner.get(f"/api/delivery-partners/{self.rider['id']}/").data["delivery_partner"]["is_available"])

    def test_cancelling_frees_the_rider_and_busy_riders_cannot_be_removed(self):
        o = self.delivery_order()
        self.assign(o)
        self.assertEqual(self.owner.delete(f"/api/delivery-partners/{self.rider['id']}/").status_code, 400)
        self.set(o, "cancelled")
        self.assertTrue(self.owner.get(f"/api/delivery-partners/{self.rider['id']}/").data["delivery_partner"]["is_available"])

    def test_rider_trip_from_pickup_to_delivered(self):
        rider = staff_login("faisal@riders.test")
        self.assertEqual(rider.get("/api/staff/me/").data["role"], "delivery")
        self.assertEqual(rider.get("/menu/api/inventory/ingredients/").status_code, 403)  # no owner tools
        o = self.delivery_order()
        self.assign(o)
        trips = rider.get("/api/delivery/my-assignments/").data
        self.assertEqual((len(trips), trips[0]["status"], trips[0]["address"]), (1, "assigned", "Beach Rd"))
        tid = trips[0]["id"]
        self.assertEqual(rider.post(f"/api/delivery/assignments/{tid}/start/").status_code, 400)  # kitchen not ready
        self.set(o, "confirmed")
        self.set(o, "ready")
        self.assertEqual(rider.post(f"/api/delivery/assignments/{tid}/start/").data["status"], "started")
        rider.post(f"/api/delivery/assignments/{tid}/location/", {"latitude": 11.27, "longitude": 75.7804, "accuracy": 12}, format="json")
        track = self.diner.get(f"/menu/api/orders/{o['id']}/public/").data
        self.assertEqual(track["tracking_status"], "out_for_delivery")
        self.assertEqual(track["delivery_partner"]["latitude"], 11.27)
        self.assertAlmostEqual(track["remaining_distance_km"], 2.0, places=0)
        self.assertGreater(track["eta_minutes"], 0)
        stranger = APIClient().get(f"/menu/api/orders/{o['id']}/public/").data
        self.assertIsNone(stranger["customer_address"])
        r = rider.post(f"/api/delivery/assignments/{tid}/delivered/")
        self.assertEqual(r.data["status"], "delivered")
        done = self.owner.get(f"/menu/api/orders/{o['id']}/").data
        self.assertEqual((done["status"], done["tracking_status"], done["payment_status"]), ("completed", "delivered", "paid"))
        self.assertTrue(Payment.objects.filter(order_id=o["id"], method="cash").exists())
        self.assertTrue(self.owner.get(f"/api/delivery-partners/{self.rider['id']}/").data["delivery_partner"]["is_available"])

    def test_a_rider_only_sees_their_own_trips(self):
        self.owner.post("/api/delivery-partners/", {"first_name": "Ann", "phone": "9847022222", "email": "ann@riders.test"}, format="json")
        ann = staff_login("ann@riders.test")
        o = self.delivery_order()
        self.assign(o)
        self.assertEqual(ann.get("/api/delivery/my-assignments/").data, [])
        tid = o["id"]
        from delivery.models import DeliveryAssignment
        tid = DeliveryAssignment.objects.get(order_id=o["id"]).id
        self.assertEqual(ann.post(f"/api/delivery/assignments/{tid}/start/").status_code, 404)
        self.assertEqual(self.owner.get("/api/delivery/my-assignments/").status_code, 403)
        self.assertTrue(mail.outbox)
