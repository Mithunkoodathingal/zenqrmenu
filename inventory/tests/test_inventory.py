"""Stock rules the owner relies on: per-branch stock, history, purchases, recipes, and stock held/used/returned by orders."""
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from common.testing import make_customer, make_menu, owner_client
from inventory.models import StockLevel
from restaurants.models import Table

ING = "/menu/api/inventory/ingredients/"


class InventoryBase(TestCase):
    def setUp(self):
        self.owner, self.r = owner_client()
        self.item, self.addon, self.table = make_menu(self.r)
        self.main = self.r.main_branch()
        self.rice = self.owner.post(ING, {"name": "Basmati rice", "unit": "kg", "stock": 10, "low_stock_threshold": 2, "unit_cost": 90}, format="json").data
        self.chicken = self.owner.post(ING, {"name": "Chicken", "unit": "kg", "stock": 5, "unit_cost": 240}, format="json").data
        r = self.owner.put(f"/api/recipes/{self.item.id}/", {"lines": [
            {"inventory_item": self.rice["id"], "quantity": 0.25}, {"inventory_item": self.chicken["id"], "quantity": 0.2}]}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.recipe = r.data

    def order(self, qty=2, table=None):
        r = APIClient().post("/menu/api/orders/", {"table": (table or self.table).id,
                                                   "items": [{"food_item_id": self.item.id, "quantity": qty}]}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def status(self, order, s):
        return self.owner.patch(f"/menu/api/orders/{order['id']}/", {"status": s}, format="json")

    def level(self, ing, branch=None):
        return StockLevel.objects.get(ingredient_id=ing["id"], branch=branch or self.main)


class IngredientTests(InventoryBase):
    def test_new_ingredient_has_opening_stock_only_at_the_chosen_branch(self):
        self.assertEqual(self.rice["stock"], 10.0)
        self.assertEqual(self.rice["status"], "in_stock")
        b2 = self.owner.post("/api/branches/", {"name": "Beach Road"}, format="json").data
        rows = self.owner.get(ING, {"branch": b2["id"]}).data
        self.assertEqual({x["name"]: x["stock"] for x in rows}, {"Basmati rice": 0.0, "Chicken": 0.0})
        self.assertTrue(all(x["status"] == "out_of_stock" for x in rows))
        hist = self.owner.get("/menu/api/inventory/history/", {"branch": self.main.id}).data
        self.assertIn("opening", [h["kind"] for h in hist])

    def test_duplicate_names_are_refused(self):
        r = self.owner.post(ING, {"name": "basmati RICE", "unit": "kg"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("name", r.data)

    def test_editing_details_never_changes_stock(self):
        r = self.owner.patch(f"{ING}{self.rice['id']}/", {"stock": 999, "low_stock_threshold": 12}, format="json")
        self.assertEqual(r.data["stock"], 10.0)
        self.assertEqual(r.data["status"], "low_stock")  # 10 available ≤ 12

    def test_ingredient_used_in_a_recipe_cannot_be_deleted(self):
        r = self.owner.delete(f"{ING}{self.rice['id']}/")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Chicken Biryani", r.data["message"])


class AdjustAndPurchaseTests(InventoryBase):
    def test_waste_adjustment_needs_a_removal_and_is_in_history(self):
        url = f"{ING}{self.rice['id']}/adjust/"
        self.assertEqual(self.owner.post(url, {"delta": 1, "reason": "waste"}, format="json").status_code, 400)
        r = self.owner.post(url, {"delta": -1.5, "reason": "waste", "note": "Spoiled"}, format="json")
        self.assertEqual(r.data["stock"], 8.5)
        h = self.owner.get("/menu/api/inventory/history/", {"kind": "adjustment"}).data[0]
        self.assertEqual((h["delta"], h["reason"], h["on_hand_after"]), (-1.5, "waste", 8.5))

    def test_other_needs_a_note_and_stock_cannot_go_below_zero(self):
        url = f"{ING}{self.rice['id']}/adjust/"
        self.assertIn("note", self.owner.post(url, {"delta": -1, "reason": "other"}, format="json").data)
        r = self.owner.post(url, {"delta": -11, "reason": "correction"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Only 10 kg", r.data["message"])

    def test_purchase_adds_stock_at_that_branch_and_updates_cost(self):
        r = self.owner.post(f"{ING}{self.rice['id']}/purchase/", {"quantity": 25, "unit_cost": 95.5, "total_cost": 1,
                                                                 "supplier": "Big Bazaar", "invoice_no": "A12", "purchased_at": "2026-11-01"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["total_cost"], 2387.5)  # server works out the total
        self.assertEqual(self.level(self.rice).on_hand, 35)
        row = self.owner.get(ING).data
        self.assertEqual(next(x for x in row if x["id"] == self.rice["id"])["unit_cost"], 95.5)
        h = self.owner.get("/menu/api/inventory/history/", {"kind": "purchase"}).data[0]
        self.assertEqual((h["delta"], h["reason"], h["note"]), (25.0, "restock", "Big Bazaar · Inv A12"))
        self.assertEqual(len(self.owner.get("/menu/api/inventory/purchases/").data), 1)

    def test_bad_purchase_is_refused(self):
        r = self.owner.post(f"{ING}{self.rice['id']}/purchase/", {"quantity": 0, "unit_cost": -1}, format="json")
        self.assertEqual(set(r.data) & {"quantity", "unit_cost"}, {"quantity", "unit_cost"})


class RecipeTests(InventoryBase):
    def test_recipe_cost_portions_and_version(self):
        # 0.25 kg × ₹90 + 0.2 kg × ₹240 = ₹70.50; portions = min(10/0.25, 5/0.2) = 25
        self.assertEqual(self.recipe["cost_per_portion"], 70.5)
        self.assertEqual(self.recipe["portions_available"], 25)
        self.assertEqual(self.recipe["version"], 1)
        r = self.owner.put(f"/api/recipes/{self.item.id}/", {"lines": [{"inventory_item": self.rice["id"], "quantity": 0.5}]}, format="json")
        self.assertEqual((r.data["version"], r.data["portions_available"]), (2, 20))

    def test_recipe_lines_are_checked(self):
        url = f"/api/recipes/{self.item.id}/"
        self.assertEqual(self.owner.put(url, {"lines": []}, format="json").status_code, 400)
        dup = [{"inventory_item": self.rice["id"], "quantity": 1}, {"inventory_item": self.rice["id"], "quantity": 2}]
        self.assertIn("twice", self.owner.put(url, {"lines": dup}, format="json").data["message"])
        self.assertEqual(self.owner.put(url, {"lines": [{"inventory_item": self.rice["id"], "quantity": 0}]}, format="json").status_code, 400)

    def test_another_restaurants_ingredient_cannot_be_used(self):
        other, _ = owner_client("other")
        theirs = other.post(ING, {"name": "Saffron", "unit": "g"}, format="json").data
        r = self.owner.put(f"/api/recipes/{self.item.id}/", {"lines": [{"inventory_item": theirs["id"], "quantity": 1}]}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(other.get(ING).data[0]["name"], "Saffron")
        self.assertEqual(len(other.get(ING).data), 1)

    def test_public_menu_marks_dish_out_of_stock(self):
        self.owner.post(f"{ING}{self.chicken['id']}/adjust/", {"delta": -4.9, "reason": "waste"}, format="json")
        order = APIClient().post("/menu/api/orders/", {"table": self.table.id, "items": [{"food_item_id": self.item.id, "quantity": 1}]}, format="json")
        self.assertEqual(order.status_code, 400)
        self.assertIn("Out of stock", order.data["message"])


class OrderStockTests(InventoryBase):
    def test_confirm_reserves_cancel_releases(self):
        o = self.order(qty=2)
        self.assertEqual(o["stock_state"], "not_reserved")
        r = self.status(o, "confirmed")
        self.assertEqual(r.data["stock_state"], "reserved")
        self.assertEqual((self.level(self.rice).on_hand, self.level(self.rice).reserved), (10, 0.5))
        held = self.owner.get("/menu/api/inventory/reservations/", {"branch": self.main.id}).data
        self.assertEqual(held[0]["order_number"], o["order_number"])
        r = self.status(o, "cancelled")
        self.assertEqual(r.data["stock_state"], "released")
        self.assertEqual((self.level(self.rice).on_hand, self.level(self.rice).reserved), (10, 0))
        self.assertEqual(self.owner.get("/menu/api/inventory/reservations/").data, [])

    def test_complete_deducts_and_writes_history(self):
        o = self.order(qty=2)
        self.status(o, "confirmed")
        self.status(o, "preparing")
        self.status(o, "ready")
        r = self.status(o, "completed")
        self.assertEqual(r.data["stock_state"], "deducted")
        self.assertEqual((self.level(self.chicken).on_hand, self.level(self.chicken).reserved), (Decimal("4.6"), 0))
        kinds = [h["kind"] for h in self.owner.get("/menu/api/inventory/history/", {"ingredient_id": self.chicken["id"]}).data]
        self.assertEqual(kinds[:2], ["deduct", "reserve"])

    def test_completing_a_pending_order_still_checks_and_uses_stock(self):
        o = self.order(qty=1)
        self.assertEqual(self.status(o, "completed").data["stock_state"], "deducted")
        self.assertEqual(self.level(self.rice).on_hand, 9.75)

    def test_shortfall_refuses_confirmation_with_409(self):
        o1, o2 = self.order(qty=20), self.order(qty=10)
        self.assertEqual(self.status(o1, "confirmed").status_code, 200)  # 20 × 0.2 = 4 kg chicken held
        r = self.status(o2, "confirmed")
        self.assertEqual(r.status_code, 409)
        self.assertIn("Chicken needs 2 kg, 1 available", r.data["message"])
        self.assertEqual(self.owner.get(f"/menu/api/orders/{o2['id']}/").data["status"], "pending")

    def test_held_stock_cannot_be_adjusted_away(self):
        self.status(self.order(qty=20), "confirmed")
        r = self.owner.post(f"{ING}{self.chicken['id']}/adjust/", {"delta": -2, "reason": "waste"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("at most 1 kg", r.data["message"])

    def test_branch_stock_is_separate(self):
        b2 = self.owner.post("/api/branches/", {"name": "Beach Road"}, format="json").data
        t2 = Table.objects.create(restaurant=self.r, branch_id=b2["id"], table_number="B1")
        r = APIClient().post("/menu/api/orders/", {"table": t2.id, "items": [{"food_item_id": self.item.id, "quantity": 1}]}, format="json")
        self.assertEqual(r.status_code, 400)  # nothing in stock at the new branch
        for ing, qty in ((self.rice, 2), (self.chicken, 2)):
            self.owner.post(f"{ING}{ing['id']}/purchase/", {"quantity": qty, "unit_cost": 1, "branch": b2["id"]}, format="json")
        o = self.order(qty=1, table=t2)
        self.assertEqual(self.status(o, "confirmed").status_code, 200)
        self.assertEqual(self.level(self.rice).reserved, 0)
        self.assertEqual(StockLevel.objects.get(ingredient_id=self.rice["id"], branch_id=b2["id"]).reserved, 0.25)

    def test_recipe_edit_does_not_change_an_open_reservation(self):
        o = self.order(qty=2)
        self.status(o, "confirmed")
        self.owner.put(f"/api/recipes/{self.item.id}/", {"lines": [{"inventory_item": self.rice["id"], "quantity": 1}]}, format="json")
        self.status(o, "completed")
        self.assertEqual(self.level(self.rice).on_hand, 9.5)  # the 0.25 × 2 that was held

    def test_dish_without_recipe_reports_no_recipe(self):
        self.owner.delete(f"/api/recipes/{self.item.id}/")
        self.assertEqual(self.order()["stock_state"], "no_recipe")


class AccessTests(InventoryBase):
    def test_diners_and_strangers_cannot_see_inventory(self):
        diner, _ = make_customer()
        self.assertEqual(diner.get(ING).status_code, 403)
        self.assertEqual(APIClient().get(ING).status_code, 401)
        other, _ = owner_client("other")
        self.assertEqual(other.get(f"{ING}{self.rice['id']}/").status_code, 404)
