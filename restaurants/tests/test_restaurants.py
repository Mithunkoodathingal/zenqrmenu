from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from common.testing import owner_client
from restaurants.models import Branch, Restaurant
from subscriptions.models import Plan


def new_owner(username="fresh"):
    user = get_user_model().objects.create_user(username, f"{username}@example.com", "pass12345!")
    c = APIClient()
    c.force_authenticate(user)
    return c, user


class ProfileTests(TestCase):
    def test_new_owner_sees_setup_form_and_empty_lists(self):
        c, _ = new_owner()
        self.assertIsNone(c.get("/menu/api/restaurant/").data["restaurant"])
        self.assertFalse(c.get("/subscription/api/subscription/").data["has_subscription"])
        self.assertEqual(c.get("/menu/api/categories/").data, [])
        self.assertEqual(c.get("/menu/api/items/").data, [])
        self.assertEqual(c.get("/menu/api/tables/").data, [])
        self.assertEqual(c.get("/api/branches/").data, [])
        self.assertEqual(c.post("/menu/api/categories/", {"name": "X"}, format="json").status_code, 404)

    def test_create_requires_phone_and_email(self):
        c, _ = new_owner()
        r = c.post("/menu/api/restaurant/", {"name": "Malabar"}, format="multipart")
        self.assertEqual(r.status_code, 400)
        self.assertIn("phone", r.data)
        self.assertIn("email", r.data)
        r = c.put("/menu/api/restaurant/", {"name": "Malabar", "phone": "123", "email": "a@b.co"}, format="multipart")
        self.assertIn("phone", r.data)

    def test_create_profile_gives_main_branch_and_free_plan(self):
        c, user = new_owner()
        r = c.put("/menu/api/restaurant/", {"name": "Malabar Kitchen", "phone": "+91 98765 43210", "email": "hi@malabar.test",
                                            "cuisines": "Kerala, Biryani, kerala", "address": "Mavoor Road"}, format="multipart")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["restaurant"]["cuisines"], ["Kerala", "Biryani"])
        restaurant = Restaurant.objects.get(owner=user)
        self.assertEqual(restaurant.branches.filter(is_main=True).count(), 1)
        status = c.get("/subscription/api/subscription/").data
        self.assertEqual(status["plan"], "free")
        self.assertTrue(status["is_active"])

    def test_google_business_link_must_be_google(self):
        c, _ = owner_client()
        r = c.patch("/menu/api/restaurant/", {"google_business_url": "https://evil.example.com/maps"}, format="json")
        self.assertIn("google_business_url", r.data)
        r = c.patch("/menu/api/restaurant/", {"google_business_url": "https://maps.app.goo.gl/abc"}, format="json")
        self.assertEqual(r.status_code, 200)


class HoursAndLocationTests(TestCase):
    def test_hours_accept_website_shape_and_return_server_shape(self):
        c, _ = owner_client()
        short = {k: {"open": True, "opens": "10:00", "closes": "21:30"} for k in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]}
        short["sun"] = {"open": False, "opens": "10:00", "closes": "21:30"}
        r = c.put("/menu/api/restaurant/working-hours/", {**short, "holidays": ["2026-12-25"]}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["monday"], {"is_open": True, "open": "10:00", "close": "21:30"})
        self.assertFalse(r.data["sunday"]["is_open"])
        self.assertEqual(r.data["holidays"], ["2026-12-25"])

    def test_hours_reject_close_before_open(self):
        c, _ = owner_client()
        r = c.put("/menu/api/restaurant/working-hours/", {"monday": {"is_open": True, "open": "22:00", "close": "09:00"}}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_location_must_be_a_real_point(self):
        c, _ = owner_client()
        self.assertEqual(c.put("/menu/api/restaurant/location/", {"latitude": 200, "longitude": 75}, format="json").status_code, 400)
        r = c.put("/menu/api/restaurant/location/", {"latitude": 11.2588, "longitude": 75.7804, "city": "Kozhikode"}, format="json")
        self.assertEqual(r.data["latitude"], 11.2588)


class BranchTests(TestCase):
    def test_create_rename_and_protect_main_branch(self):
        c, restaurant = owner_client()
        r = c.post("/api/branches/", {"name": "Kallai Road", "city": "Kozhikode"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertFalse(r.data["is_main"])
        self.assertEqual(c.post("/api/branches/", {"name": "kallai road"}, format="json").status_code, 400)
        main = restaurant.main_branch()
        self.assertEqual(c.delete(f"/api/branches/{main.id}/").status_code, 400)
        self.assertEqual(c.patch(f"/api/branches/{main.id}/", {"is_active": False}, format="json").status_code, 400)
        # Make the new branch main; the old main stops being main.
        c.patch(f"/api/branches/{r.data['id']}/", {"is_main": True}, format="json")
        self.assertEqual(Branch.objects.get(pk=r.data["id"]).is_main, True)
        self.assertEqual(Branch.objects.get(pk=main.id).is_main, False)

    def test_other_owner_cannot_touch_my_branch(self):
        c, restaurant = owner_client()
        other, _ = owner_client("other")
        self.assertEqual(other.delete(f"/api/branches/{restaurant.main_branch().id}/").status_code, 204)  # not found = no-op
        self.assertTrue(Branch.objects.filter(pk=restaurant.main_branch().id).exists())
        self.assertEqual(other.patch(f"/api/branches/{restaurant.main_branch().id}/", {"name": "x"}, format="json").status_code, 404)


class TableAndQrTests(TestCase):
    def test_free_plan_allows_one_table(self):
        c, _ = owner_client()
        self.assertEqual(c.post("/menu/api/tables/", {"table_number": 1}, format="json").status_code, 201)
        r = c.post("/menu/api/tables/", {"table_number": 2}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertIn("limit", r.data["message"])

    def test_duplicate_table_number_rejected(self):
        Plan.objects.create(name="Big", price=0, table_limit=0, position=0)
        c, _ = owner_client()
        c.post("/menu/api/tables/", {"table_number": "A1"}, format="json")
        self.assertEqual(c.post("/menu/api/tables/", {"table_number": "a1"}, format="json").status_code, 400)

    def test_qr_links_point_to_the_website(self):
        c, restaurant = owner_client()
        t = c.post("/menu/api/tables/", {"table_number": 1}, format="json").data
        self.assertEqual(c.get(f"/menu/api/qr/table/{t['id']}/").data["url"], f"http://frontend.test/menu/{t['id']}")
        self.assertEqual(c.get("/menu/api/qr/pickup/").data["url"], f"http://frontend.test/pickup?restaurant={restaurant.id}")
        self.assertTrue(c.get("/menu/api/qr/delivery/").data["image"].startswith("data:image/png;base64,"))


class PublicDiscoveryTests(TestCase):
    def setUp(self):
        self.c, self.r = owner_client(latitude="11.258800", longitude="75.780400", enable_delivery=True,
                                      max_delivery_km=8, free_delivery_km=3, charge_per_extra_km=10)
        self.c.post("/menu/api/tables/", {"table_number": 1}, format="json")

    def test_nearby_lists_restaurants_by_distance(self):
        _, far = owner_client("far", latitude="11.300000", longitude="75.800000")
        far.tables.create(branch=far.main_branch(), table_number="1")
        _, no_tables = owner_client("notables", latitude="11.259000", longitude="75.780500")
        rows = APIClient().get("/api/public/restaurants/nearby/", {"lat": 11.2588, "lng": 75.7804, "radius": 10}).data
        self.assertEqual([r["id"] for r in rows], [self.r.id, far.id])  # no table = diners can't open a menu yet
        self.assertTrue(rows[0]["href"].startswith("/menu/"))
        self.assertTrue(rows[0]["delivery_available"])

    def test_delivery_quote_charges_beyond_free_distance(self):
        # ~5.5 km north: 2.5 km beyond the free 3 km at ₹10/km
        q = APIClient().post("/menu/api/delivery/quote/", {"restaurant_id": self.r.id, "latitude": 11.3083, "longitude": 75.7804}, format="json").data
        self.assertAlmostEqual(q["distance_km"], 5.5, delta=0.1)
        self.assertAlmostEqual(q["delivery_charge"], 25, delta=1.5)
        self.assertTrue(q["inside_area"])
        q = APIClient().post("/menu/api/delivery/quote/", {"restaurant_id": self.r.id, "latitude": 11.40, "longitude": 75.7804}, format="json").data
        self.assertFalse(q["inside_area"])
