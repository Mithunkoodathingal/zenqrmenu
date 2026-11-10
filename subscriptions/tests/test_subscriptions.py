import hashlib
import hmac
from datetime import timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from common.testing import owner_client
from subscriptions.models import Plan
from subscriptions.services import active_plan, ensure_subscription


@override_settings(RAZORPAY_KEY_ID="rzp_test_Platform1", RAZORPAY_KEY_SECRET="platform-secret")
class PlanPurchaseTests(TestCase):
    def setUp(self):
        self.c, self.r = owner_client()
        self.basic = Plan.objects.create(name="Basic", price=299, duration_days=30, table_limit=10)

    @mock.patch("payments.gateway.create_order", return_value={"id": "order_PLAN1"})
    def test_paid_plan_activates_for_30_days_after_verified_payment(self, _):
        created = self.c.post("/subscription/api/create/", {"plan_id": self.basic.id}, format="json").data
        self.assertEqual(created["amount"], 29900)
        sig = hmac.new(b"platform-secret", b"order_PLAN1|pay_9", hashlib.sha256).hexdigest()
        r = self.c.post("/subscription/api/verify/", {"razorpay_order_id": "order_PLAN1", "razorpay_payment_id": "pay_9",
                                                      "razorpay_signature": sig}, format="json")
        self.assertTrue(r.data["success"], r.data)
        sub = ensure_subscription(self.r)
        self.assertEqual(active_plan(self.r), self.basic)
        self.assertAlmostEqual((sub.renews_at - timezone.now()).days, 29, delta=1)
        self.assertEqual(self.c.get("/subscription/api/invoices/").data[0]["amount"], 299.0)

    @mock.patch("payments.gateway.create_order", return_value={"id": "order_PLAN2"})
    def test_bad_signature_does_not_upgrade(self, _):
        self.c.post("/subscription/api/create/", {"plan_id": self.basic.id}, format="json")
        r = self.c.post("/subscription/api/verify/", {"razorpay_order_id": "order_PLAN2", "razorpay_payment_id": "p",
                                                      "razorpay_signature": "x"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(active_plan(self.r).price, 0)

    def test_cancelled_plan_works_until_its_end_date_then_free(self):
        sub = ensure_subscription(self.r)
        sub.plan, sub.renews_at = self.basic, timezone.now() + timedelta(days=5)
        sub.save()
        self.c.post("/subscription/api/cancel/")
        self.assertEqual(active_plan(self.r), self.basic)
        sub.refresh_from_db()
        sub.renews_at = timezone.now() - timedelta(minutes=1)
        sub.save()
        self.assertEqual(active_plan(self.r).price, 0)
