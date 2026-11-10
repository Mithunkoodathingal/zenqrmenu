"""Staff accounts: owner-only changes, invite-to-login, role limits, and shift/break records."""
import re

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from common.testing import make_customer, owner_client

PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")


def staff_login(email, password="Kitchen#2026"):
    """Follow the invite email's set-password link, then log in like the website does."""
    body = mail.outbox[-1].body
    uid, token = re.search(r"uid=([^&]+)&token=(\S+)", body).groups()
    c = APIClient()
    r = c.post("/api/password/reset/confirm/", {"uid": uid, "token": token, "new_password1": password, "new_password2": password}, format="json")
    assert r.status_code == 200, r.data
    r = c.post("/api/login/", {"username": email, "password": password}, format="json")
    assert r.status_code == 200, r.data
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return c


class StaffTests(TestCase):
    def setUp(self):
        self.owner, self.r = owner_client()

    def add(self, **extra):
        body = {"first_name": "Ravi", "last_name": "K", "employee_id": "emp01", "phone": "9847000001", "role": "cashier", **extra}
        return self.owner.post("/api/staff/create/", body, format="json")

    def test_owner_adds_staff_with_photo_and_they_get_a_login(self):
        photo = SimpleUploadedFile("ravi.png", PNG, content_type="image/png")
        r = self.owner.post("/api/staff/create/", {"first_name": "Ravi", "employee_id": "emp01", "phone": "9847000001",
                                                   "role": "chef", "email": "ravi@malabar.test", "profile_photo": photo}, format="multipart")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.data["employee_id"], r.data["has_login"]), ("EMP01", True))
        self.assertTrue(r.data["profile_photo"].startswith("http"))
        self.assertIn("Choose your password", mail.outbox[-1].body)
        chef = staff_login("ravi@malabar.test")
        me = chef.get("/api/staff/me/").data
        self.assertEqual((me["role"], me["restaurant_id"]), ("chef", self.r.id))
        self.assertEqual(chef.get("/kds/orders/").status_code, 200)
        self.assertEqual(chef.get("/api/staff/").status_code, 403)  # chefs don't manage staff
        self.assertEqual(chef.get("/payments/api/payment-settings/").status_code, 403)

    def test_manager_can_view_staff_but_only_the_owner_changes_them(self):
        self.add(role="manager", email="mgr@malabar.test", employee_id="M1")
        mgr = staff_login("mgr@malabar.test")
        self.assertEqual(len(mgr.get("/api/staff/").data), 1)
        r = mgr.post("/api/staff/create/", {"first_name": "Anu", "employee_id": "E2", "role": "owner"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_bad_details_are_refused(self):
        self.add()
        r = self.add(employee_id="EMP01")
        self.assertIn("employee_id", r.data)
        self.assertIn("role", self.add(employee_id="X9", role="boss").data)
        self.assertIn("first_name", self.add(employee_id="X8", first_name="R").data)

    def test_a_diner_email_cannot_become_staff(self):
        make_customer("asha@diner.test")
        r = self.add(email="asha@diner.test")
        self.assertEqual(r.status_code, 400)
        self.assertIn("email", r.data)

    def test_removed_staff_can_no_longer_log_in(self):
        sid = self.add(email="ravi@malabar.test").data["id"]
        staff_login("ravi@malabar.test")
        self.assertEqual(self.owner.delete(f"/api/staff/{sid}/delete/").status_code, 204)
        r = APIClient().post("/api/login/", {"username": "ravi@malabar.test", "password": "Kitchen#2026"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_shift_and_break_records(self):
        sid = self.add().data["id"]
        url = f"/api/staff/{sid}/shift/"
        self.assertEqual(self.owner.patch(url, {"action": "start_break"}, format="json").status_code, 400)
        self.assertEqual(self.owner.patch(url, {"action": "clock_in"}, format="json").data["shift_status"], "on_shift")
        self.assertEqual(self.owner.patch(url, {"action": "clock_in"}, format="json").status_code, 400)
        self.assertEqual(self.owner.patch(url, {"action": "start_break"}, format="json").data["shift_status"], "on_break")
        # "On shift" while on a break ends the break (the website sends clock_in for that)
        self.assertEqual(self.owner.patch(url, {"action": "clock_in"}, format="json").data["shift_status"], "on_shift")
        self.assertEqual(self.owner.patch(url, {"action": "clock_out"}, format="json").data["shift_status"], "off_shift")
        att = self.owner.get("/staff/attendance/", {"staff_id": sid}).data
        self.assertEqual(len(att), 1)
        self.assertIsNotNone(att[0]["clock_out"])
        brk = self.owner.get("/staff/breaks/").data
        self.assertEqual((len(brk), brk[0]["duration_minutes"]), (1, 0))

    def test_other_restaurants_cannot_see_staff(self):
        sid = self.add().data["id"]
        other, _ = owner_client("other")
        self.assertEqual(other.get("/api/staff/").data, [])
        self.assertEqual(other.get(f"/api/staff/{sid}/").status_code, 404)
