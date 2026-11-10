import re

from django.core import mail
from rest_framework.test import APIClient

from django.test import TestCase

from common.testing import make_customer, make_owner, owner_client


class DinerSignInTests(TestCase):
    def setUp(self):
        self.c = APIClient()

    def _code(self):
        return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)

    def test_register_with_emailed_code_gives_verified_session(self):
        r = self.c.post("/api/customers/auth/email/request-otp/", {"email": "New@Example.com", "intent": "register"}, format="json")
        self.assertEqual(r.status_code, 200)
        r = self.c.post("/api/customers/auth/email/verify-otp/",
                        {"email": "new@example.com", "code": self._code(), "name": "Ravi", "marketing_opt_in": True}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["customer"]["email_verified"])
        self.assertEqual(r.data["customer"]["name"], "Ravi")
        self.assertIsNotNone(r.data["customer"]["marketing_consent_at"])
        me = APIClient()
        me.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
        self.assertEqual(me.get("/api/customers/me/").data["email"], "new@example.com")

    def test_login_for_unknown_email_is_refused(self):
        r = self.c.post("/api/customers/auth/email/request-otp/", {"email": "nobody@example.com", "intent": "login"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Create one instead", r.data["message"])

    def test_five_wrong_codes_lock_the_code(self):
        self.c.post("/api/customers/auth/email/request-otp/", {"email": "a@example.com", "intent": "register"}, format="json")
        good = self._code()
        bad = "000000" if good != "000000" else "111111"
        for _ in range(5):
            self.c.post("/api/customers/auth/email/verify-otp/", {"email": "a@example.com", "code": bad}, format="json")
        r = self.c.post("/api/customers/auth/email/verify-otp/", {"email": "a@example.com", "code": good}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_diner_token_cannot_use_restaurant_tools(self):
        client, _ = make_customer()
        self.assertEqual(client.get("/menu/api/restaurant/").status_code, 403)
        self.assertEqual(client.get("/menu/api/orders/").status_code, 403)

    def test_owner_login_still_works_when_a_diner_shares_the_email(self):
        user, _ = make_owner("chef")
        user.owner_account if hasattr(user, "owner_account") else None
        from accounts.models import OwnerAccount
        OwnerAccount.objects.update_or_create(user=user, defaults={"email_verified": True})
        make_customer(email="chef@example.com")
        r = self.c.post("/api/login/", {"username": "chef@example.com", "password": "pass12345!"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["user"]["username"], "chef")


class AddressTests(TestCase):
    def setUp(self):
        self.c, self.me = make_customer()

    def _add(self, label):
        return self.c.post("/api/customers/me/addresses/", {"label": label, "recipient_name": "Asha", "phone": "9800000001",
                                                             "house": "12A", "city": "Kozhikode", "latitude": 11.25, "longitude": 75.78},
                           format="json").data

    def test_first_address_is_default_and_default_moves(self):
        home, work = self._add("Home"), self._add("Work")
        self.assertTrue(home["is_default"])
        self.assertFalse(work["is_default"])
        self.c.post(f"/api/customers/me/addresses/{work['id']}/set-default/")
        rows = {a["label"]: a["is_default"] for a in self.c.get("/api/customers/me/addresses/").data}
        self.assertEqual(rows, {"Home": False, "Work": True})
        self.c.delete(f"/api/customers/me/addresses/{work['id']}/")
        self.assertTrue(self.c.get("/api/customers/me/addresses/").data[0]["is_default"])

    def test_cannot_touch_another_diners_address(self):
        mine = self._add("Home")
        other, _ = make_customer("other@example.com")
        self.assertEqual(other.patch(f"/api/customers/me/addresses/{mine['id']}/", {"city": "X"}, format="json").status_code, 404)

    def test_address_needs_phone(self):
        r = self.c.post("/api/customers/me/addresses/", {"recipient_name": "A", "house": "1", "city": "K", "phone": "12"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("phone", r.data)
