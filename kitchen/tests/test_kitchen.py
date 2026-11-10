"""Kitchen display: finished orders stay on the board after refreshes; priority and notes; same status rules as orders."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from common.testing import make_menu, owner_client
from orders.models import Order


class KitchenTests(TestCase):
    def setUp(self):
        self.owner, self.r = owner_client()
        self.item, _, self.table = make_menu(self.r)

    def order(self):
        return APIClient().post("/menu/api/orders/", {"table": self.table.id, "items": [{"food_item_id": self.item.id, "quantity": 1}]},
                                format="json").data

    def test_completed_orders_stay_on_the_board_between_polls(self):
        a, b = self.order(), self.order()
        self.owner.patch(f"/menu/api/orders/{a['id']}/", {"status": "completed"}, format="json")
        for _ in range(2):  # two polls
            board = {o["id"]: o["status"] for o in self.owner.get("/kds/orders/").data}
            self.assertEqual(board, {a["id"]: "completed", b["id"]: "pending"})
        Order.objects.filter(pk=a["id"]).update(updated_at=timezone.now() - timedelta(hours=13))
        self.assertEqual([o["id"] for o in self.owner.get("/kds/orders/").data], [b["id"]])

    def test_board_rows_have_what_the_kitchen_reads(self):
        o = self.order()
        self.owner.patch(f"/kds/orders/{o['id']}/priority/", {"kitchen_priority": "urgent"}, format="json")
        self.owner.post(f"/kds/orders/{o['id']}/notes/", {"note": "No onions", "note_type": "kitchen", "is_internal": True, "is_pinned": True}, format="json")
        row = self.owner.get("/kds/orders/").data[0]
        self.assertEqual(row["kitchen_priority"], "urgent")
        self.assertEqual(row["kitchen_notes"][0]["note"], "No onions")
        self.assertEqual(row["order_items"][0]["food_item_name"], "Chicken Biryani")
        self.assertEqual(self.owner.patch(f"/kds/orders/{o['id']}/priority/", {"kitchen_priority": "asap"}, format="json").status_code, 400)

    def test_kitchen_status_mirror_follows_order_rules(self):
        o = self.order()
        self.owner.patch(f"/menu/api/orders/{o['id']}/", {"status": "confirmed"}, format="json")
        r = self.owner.patch(f"/kds/orders/{o['id']}/status/", {"kitchen_status": "confirmed"}, format="json")
        self.assertEqual(r.data["status"], "confirmed")  # same status: nothing changes
        self.owner.patch(f"/menu/api/orders/{o['id']}/", {"status": "completed"}, format="json")
        self.assertEqual(self.owner.patch(f"/kds/orders/{o['id']}/status/", {"kitchen_status": "preparing"}, format="json").status_code, 400)

    def test_notes_archive_and_statistics(self):
        o = self.order()
        n = self.owner.post("/kitchen/notes/", {"note": "Fryer 2 down", "is_pinned": True}, format="json").data
        self.assertEqual(len(self.owner.get("/kitchen/notes/").data), 1)
        self.owner.delete(f"/kitchen/notes/{n['id']}/")
        self.assertEqual(self.owner.get("/kitchen/notes/").data, [])
        self.owner.patch(f"/menu/api/orders/{o['id']}/", {"status": "confirmed"}, format="json")
        stats = self.owner.get("/kds/statistics/").data
        self.assertEqual((stats["total_orders"], stats["confirmed"]), (1, 1))

    def test_other_restaurants_cannot_touch_the_board(self):
        o = self.order()
        other, _ = owner_client("other")
        self.assertEqual(other.get("/kds/orders/").data, [])
        self.assertEqual(other.patch(f"/kds/orders/{o['id']}/priority/", {"kitchen_priority": "high"}, format="json").status_code, 404)
