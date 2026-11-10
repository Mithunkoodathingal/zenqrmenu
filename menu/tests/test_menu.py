from django.test import TestCase
from rest_framework.test import APIClient

from common.testing import owner_client
from menu.models import FoodItem


class MenuTests(TestCase):
    def setUp(self):
        self.c, self.r = owner_client()
        self.cat = self.c.post("/menu/api/categories/", {"name": "Biryani"}, format="json").data
        self.table = self.c.post("/menu/api/tables/", {"table_number": 1}, format="json").data

    def item(self, **extra):
        body = {"name": "Chicken Biryani", "price": 224, "category": self.cat["id"], "description": "Kaima rice", **extra}
        return self.c.post("/menu/api/items/", body, format="json")

    def test_selling_price_is_charged_and_original_only_kept_when_higher(self):
        r = self.item(original_price=280)
        self.assertEqual(r.status_code, 201)
        self.assertEqual((r.data["price"], r.data["original_price"], r.data["discount_percent"]), (224.0, 280.0, 20))
        r = self.c.patch(f"/menu/api/items/{r.data['id']}/", {"original_price": 200}, format="json")
        self.assertIsNone(r.data["original_price"])
        self.assertEqual(self.item(name="Free", price=0).status_code, 400)

    def test_veg_flag_and_pause_from_any_website_key(self):
        r = self.item(food_type="non_veg", is_paused=True)
        self.assertFalse(r.data["is_veg"])
        self.assertFalse(r.data["is_available"])
        r = self.c.patch(f"/menu/api/items/{r.data['id']}/", {"is_available": True, "veg": True}, format="json")
        self.assertTrue(r.data["is_available"] and r.data["is_veg"])

    def test_addons_are_saved_replaced_and_shown_publicly(self):
        r = self.item(addons=[{"name": "Extra raita", "price": 20}, {"name": "Egg", "price": 15}])
        self.assertEqual([a["name"] for a in r.data["addons"]], ["Extra raita", "Egg"])
        keep = r.data["addons"][0]
        r = self.c.patch(f"/menu/api/items/{r.data['id']}/", {"addons": [keep]}, format="json")
        self.assertEqual(len(r.data["addons"]), 1)
        public = APIClient().get(f"/menu/api/table/{self.table['id']}/").data
        self.assertEqual(public["items"][0]["addons"][0]["price"], 20.0)

    def test_branch_price_and_hidden_items_apply_on_that_branch_only(self):
        item = self.item().data
        other = self.item(name="Veg Biryani", price=180).data
        branch = self.c.post("/api/branches/", {"name": "Beach Road"}, format="json").data
        beach_table = self.c.post("/menu/api/tables/", {"table_number": "B1", "branch": branch["id"]}, format="json")
        # Free plan allows one table; lift the limit for this check.
        if beach_table.status_code == 403:
            from subscriptions.models import Plan, Subscription
            Subscription.objects.filter(restaurant=self.r).update(plan=Plan.objects.create(name="Big", price=0, table_limit=0, position=0))
            beach_table = self.c.post("/menu/api/tables/", {"table_number": "B1", "branch": branch["id"]}, format="json")
        self.c.put(f"/api/branches/{branch['id']}/menu-overrides/", {"food_item": item["id"], "is_available": None, "price": 239}, format="json")
        self.c.put(f"/api/branches/{branch['id']}/menu-overrides/", {"food_item": other["id"], "is_available": False, "price": None}, format="json")
        beach = {i["id"]: i for i in APIClient().get(f"/menu/api/table/{beach_table.data['id']}/").data["items"]}
        main = {i["id"]: i for i in APIClient().get(f"/menu/api/table/{self.table['id']}/").data["items"]}
        self.assertEqual(beach[item["id"]]["price"], 239.0)
        self.assertEqual(main[item["id"]]["price"], 224.0)
        self.assertEqual(beach[other["id"]]["unavailable_reason"], "Not served at this branch")
        self.assertTrue(main[other["id"]]["is_available"])
        # Hiding a category removes it and its items at that branch.
        self.c.put(f"/api/branches/{branch['id']}/category-overrides/", {"category": self.cat["id"], "is_available": False}, format="json")
        data = APIClient().get(f"/menu/api/table/{beach_table.data['id']}/").data
        self.assertEqual((data["categories"], data["items"]), ([], []))

    def test_owners_cannot_see_or_edit_each_others_menus(self):
        item = self.item().data
        other, _ = owner_client("other")
        self.assertEqual(other.get("/menu/api/items/").data, [])
        self.assertEqual(other.patch(f"/menu/api/items/{item['id']}/", {"price": 1}, format="json").status_code, 404)
        self.assertEqual(other.post("/menu/api/items/", {"name": "x", "price": 10, "category": self.cat["id"]}, format="json").status_code, 400)
        self.assertEqual(FoodItem.objects.get(pk=item["id"]).price, 224)

    def test_public_menu_shows_restaurant_card(self):
        self.item()
        data = APIClient().get(f"/menu/api/table/{self.table['id']}/").data
        self.assertEqual(data["restaurant"]["name"], "Malabar Kitchen")
        self.assertEqual(data["table_number"], "1")
        self.assertEqual(data["branch_name"], "Main branch")
