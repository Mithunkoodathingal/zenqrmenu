import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from rest_framework.test import APIClient


class OwnerAuthTests(TestCase):
    def setUp(self):
        self.c = APIClient()

    def register(self, username="malabar", email="owner@malabar.test"):
        with self.captureOnCommitCallbacks(execute=True):
            return self.c.post("/api/register/", {"username": username, "email": email,
                                                  "password1": "Str0ng-pass!", "password2": "Str0ng-pass!"}, format="json")

    def test_register_requires_email_confirmation_before_login(self):
        self.assertEqual(self.register().status_code, 201)
        r = self.c.post("/api/login/", {"username": "malabar", "password": "Str0ng-pass!"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.data["error"], "Email not verified")  # the website routes to /verify-email on this exact text
        link = re.search(r"https?://\S+", mail.outbox[-1].body).group(0)
        r = self.c.get(link.replace("http://testserver", ""))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r["Location"].endswith("/login?verified=1"))
        r = self.c.post("/api/login/", {"username": "owner@malabar.test", "password": "Str0ng-pass!"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["access"] and r.data["refresh"])
        self.assertEqual(r.data["user"]["username"], "malabar")
        self.c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
        self.assertEqual(self.c.get("/api/auth/user/").data["user"]["email"], "owner@malabar.test")
        refreshed = APIClient().post("/api/auth/refresh/", {"refresh": r.data["refresh"]}, format="json")
        self.assertIn("access", refreshed.data)

    def test_register_rejects_mismatch_and_duplicates(self):
        r = self.c.post("/api/register/", {"username": "a", "email": "a@x.com", "password1": "Str0ng-pass!", "password2": "nope"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("password2", r.data["errors"])
        self.register()
        r = self.register("malabar", "other@x.com")
        self.assertIn("username", r.data["errors"])

    def test_wrong_password_and_bad_refresh(self):
        self.register()
        r = self.c.post("/api/login/", {"username": "malabar", "password": "wrong"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(APIClient().post("/api/auth/refresh/", {"refresh": "junk"}, format="json").status_code, 401)

    def test_password_reset_link_sets_new_password(self):
        self.register()
        self.c.post("/api/password/reset/", {"email": "owner@malabar.test"}, format="json")
        link = mail.outbox[-1].body
        uid = re.search(r"uid=([^&\s]+)", link).group(1)
        token = re.search(r"token=([^&\s]+)", link).group(1)
        r = self.c.post("/api/password/reset/confirm/", {"uid": uid, "token": token, "new_password1": "N3w-pass-word!", "new_password2": "N3w-pass-word!"}, format="json")
        self.assertEqual(r.status_code, 200)
        r = self.c.post("/api/login/", {"username": "malabar", "password": "N3w-pass-word!"}, format="json")
        self.assertEqual(r.status_code, 200)  # resetting by email also confirms the email

    def test_reset_with_bad_token_fails(self):
        self.register()
        user = get_user_model().objects.get(username="malabar")
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        r = self.c.post("/api/password/reset/confirm/", {"uid": urlsafe_base64_encode(force_bytes(user.pk)), "token": "bad",
                                                          "new_password1": "N3w-pass-word!", "new_password2": "N3w-pass-word!"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_google_sign_in_reports_when_not_configured(self):
        self.assertEqual(self.c.post("/api/auth/google/", {"id_token": "x"}, format="json").status_code, 503)
