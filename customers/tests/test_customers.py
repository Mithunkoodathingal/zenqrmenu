import re

from django.core import mail
from rest_framework.test import APIClient

from django.test import TestCase

from common.testing import make_customer, make_owner, owner_client


class DinerSignInTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.c = APIClient()

    def _code(self):
        return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)

    def _register(self, email="new@example.com", pw="Tasty2026x"):
        return self.c.post("/api/customers/auth/register/", {"email": email, "name": "Ravi", "password": pw, "marketing_opt_in": True}, format="json")

    def _login(self, email="new@example.com", pw="Tasty2026x"):
        return self.c.post("/api/customers/auth/login/", {"email": email, "password": pw}, format="json")

    def _verify(self, code, email="new@example.com"):
        return self.c.post("/api/customers/auth/verify-email/", {"email": email, "code": code}, format="json")

    def test_1_to_3_register_sends_code_to_that_email_and_code_activates(self):
        r = self._register("New@Example.com")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(mail.outbox[-1].to, ["new@example.com"])
        self.assertNotIn("code", r.data)
        self.assertEqual(self._login().status_code, 400)  # not active before verification
        r = self._verify(self._code())
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["customer"]["email_verified"])
        self.assertIsNotNone(r.data["customer"]["marketing_consent_at"])

    def test_4_wrong_code_rejected_and_five_lock(self):
        self._register()
        good = self._code(); bad = "000000" if good != "000000" else "111111"
        self.assertEqual(self._verify(bad).status_code, 400)
        for _ in range(4):
            self._verify(bad)
        self.assertEqual(self._verify(good).status_code, 400)

    def test_5_expired_code_rejected(self):
        from datetime import timedelta
        from django.utils import timezone
        from customers.models import EmailCode
        self._register()
        code = self._code()
        EmailCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self._verify(code).status_code, 400)

    def test_6_resend_is_rate_limited_then_works(self):
        from datetime import timedelta
        from customers.models import EmailCode
        self._register()
        r = self.c.post("/api/customers/auth/resend-code/", {"email": "new@example.com"}, format="json")
        self.assertEqual(r.status_code, 429)
        EmailCode.objects.update(created_at=EmailCode.objects.first().created_at - timedelta(minutes=2))
        n = len(mail.outbox)
        r = self.c.post("/api/customers/auth/resend-code/", {"email": "new@example.com"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), n + 1)
        self.assertEqual(self._verify(self._code()).status_code, 200)

    def test_7_to_9_password_login_without_code_and_wrong_password(self):
        self._register(); self._verify(self._code())
        n = len(mail.outbox)
        r = self._login()
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
        self.assertEqual(self._login().status_code, 200)
        self.assertEqual(len(mail.outbox), n)  # no code on sign-in
        r = self._login(pw="wrong-pass1")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["message"] if "message" in r.data else r.data["detail"], "Email or password is incorrect.")

    def test_repeated_wrong_passwords_lock_for_a_while(self):
        self._register(); self._verify(self._code())
        for _ in range(5):
            self._login(pw="wrong-pass1")
        self.assertEqual(self._login().status_code, 429)

    def test_unknown_email_gets_the_same_reply(self):
        self.assertEqual(self._login("nobody@example.com").data, self._login(pw="nope12345").data)

    def test_registering_an_existing_email_does_not_reveal_or_take_it_over(self):
        client, p = make_customer(email="asha@example.com")
        p.user.set_password("Original99"); p.user.save()
        r = self._register("asha@example.com", "Hijack2026x")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self._login("asha@example.com", "Hijack2026x").status_code, 400)
        self.assertEqual(self._login("asha@example.com", "Original99").status_code, 200)

    def test_weak_password_refused(self):
        self.assertEqual(self._register(pw="short").status_code, 400)

    def _reset_link(self):
        body = mail.outbox[-1].body
        return re.search(r"uid=([^&\s]+)&token=([^\s]+)", body).groups()

    def test_10_to_12_forgot_password_email_link_and_new_password(self):
        self._register(); self._verify(self._code())
        r = self.c.post("/api/customers/auth/password/forgot/", {"email": "new@example.com"}, format="json")
        self.assertEqual(r.status_code, 200)
        uid, token = self._reset_link()
        r = self.c.post("/api/customers/auth/password/reset/", {"uid": uid, "token": token, "password": "Fresh2026y"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self._login(pw="Fresh2026y").status_code, 200)
        self.assertEqual(self._login(pw="Tasty2026x").status_code, 400)
        r = self.c.post("/api/customers/auth/password/reset/", {"uid": uid, "token": token, "password": "Again2026z"}, format="json")
        self.assertEqual(r.status_code, 400)  # single use

    def test_11_reset_link_expires(self):
        from django.test import override_settings
        self._register(); self._verify(self._code())
        self.c.post("/api/customers/auth/password/forgot/", {"email": "new@example.com"}, format="json")
        uid, token = self._reset_link()
        import time
        with override_settings(PASSWORD_RESET_TIMEOUT=0):
            time.sleep(1.1)
            r = self.c.post("/api/customers/auth/password/reset/", {"uid": uid, "token": token, "password": "Fresh2026y"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_reset_never_activates_unverified_account(self):
        self._register()
        n = len(mail.outbox)
        self.c.post("/api/customers/auth/password/forgot/", {"email": "new@example.com"}, format="json")
        self.assertEqual(len(mail.outbox), n)

    def test_13_14_existing_code_only_diner_sets_password_and_keeps_data(self):
        client, p = make_customer(email="old@example.com")
        p.user.set_unusable_password(); p.user.save()
        client.post("/api/customers/me/addresses/", {"label": "Home", "recipient_name": "Asha", "phone": "9800000001", "house": "1", "city": "Kozhikode"}, format="json")
        r = self._login("old@example.com", "anything1")
        self.assertEqual(r.data.get("code"), "password_not_set")
        self.c.post("/api/customers/auth/password/forgot/", {"email": "old@example.com"}, format="json")
        uid, token = self._reset_link()
        self.c.post("/api/customers/auth/password/reset/", {"uid": uid, "token": token, "password": "Mine2026ok"}, format="json")
        r = self._login("old@example.com", "Mine2026ok")
        self.assertEqual(r.status_code, 200)
        me = APIClient(); me.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
        self.assertEqual(len(me.get("/api/customers/me/addresses/").data), 1)
        self.assertEqual(me.get("/api/customers/me/").data["name"], "Asha")

    def test_change_password_needs_current(self):
        self._register(); self._verify(self._code())
        tok = self._login().data["access"]
        me = APIClient(); me.credentials(HTTP_AUTHORIZATION=f"Bearer {tok}")
        self.assertEqual(me.post("/api/customers/me/password/", {"current_password": "bad", "new_password": "Next2026ab"}, format="json").status_code, 400)
        self.assertEqual(me.post("/api/customers/me/password/", {"current_password": "Tasty2026x", "new_password": "Next2026ab"}, format="json").status_code, 200)
        self.assertEqual(self._login(pw="Next2026ab").status_code, 200)

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
