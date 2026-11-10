import hashlib
import hmac
from decimal import Decimal
from unittest import mock

from rest_framework.test import APIClient

from orders.models import Order
from orders.tests.test_orders import OrderTestBase
from payments.models import BranchPaymentAccount, PaymentIncentive, PaymentSettings
from payments.routing import routes_to
from restaurants.models import Branch

KEY, SECRET = "rzp_test_Parent123", "parent-secret-123"


def sign(secret, order_id, payment_id):
    return hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()


class PaymentTests(OrderTestBase):
    def setUp(self):
        super().setUp()
        s = PaymentSettings(restaurant=self.r, razorpay_key_id=KEY, accept_online=True, environment="test", verified=True)
        s.key_secret = SECRET
        s.save()

    def test_secret_is_never_returned(self):
        data = self.owner.get("/payments/api/payment-settings/").data
        self.assertTrue(data["has_key_secret"])
        self.assertNotIn(SECRET, str(data))

    def test_online_needs_saved_keys(self):
        PaymentSettings.objects.all().delete()
        r = self.owner.post("/payments/api/payment-settings/", {"accept_online": True}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_online_incentive_takes_5_percent_off_online_pickup(self):
        PaymentIncentive.objects.create(restaurant=self.r, enabled=True, type="percent", value=5, order_types=["pickup"])
        online = self.pickup(payment_method="online")
        self.assertEqual(online.data["online_discount"], 10.0)
        self.assertEqual(online.data["total_price"], 190.0)
        self.assertEqual(self.pickup(payment_method="cash").data["total_price"], 200.0)

    def test_branch_with_unverified_own_account_falls_back_to_parent(self):
        b = Branch.objects.create(restaurant=self.r, name="Beach")
        a = BranchPaymentAccount(branch=b, mode="own", razorpay_key_id="rzp_test_Beach999")
        a.key_secret = "beach-secret"
        a.save()
        self.assertEqual(routes_to(b), {"key_id": KEY, "merchant": "Restaurant account", "source": "parent_fallback"})
        a.verified = True
        a.save()
        self.assertEqual(routes_to(b)["source"], "branch")
        self.assertEqual(routes_to(b)["key_id"], "rzp_test_Beach999")

    @mock.patch("payments.gateway.create_order", return_value={"id": "order_RZ1"})
    def test_online_payment_is_confirmed_only_with_a_valid_signature(self, _):
        oid = self.pickup(payment_method="online").data["id"]
        self.assertEqual(self.owner.patch(f"/menu/api/orders/{oid}/", {"status": "confirmed"}, format="json").status_code, 400)
        created = self.diner.post(f"/payments/orders/{oid}/create-payment/").data
        self.assertEqual(created["amount"], 20000)
        self.assertEqual(created["key"], KEY)
        bad = self.diner.post(f"/payments/orders/{oid}/verify-payment/", {"razorpay_order_id": "order_RZ1", "razorpay_payment_id": "pay_1",
                                                                          "razorpay_signature": "nope"}, format="json")
        self.assertEqual(bad.status_code, 400)
        self.diner.post(f"/payments/orders/{oid}/create-payment/")
        ok = self.diner.post(f"/payments/orders/{oid}/verify-payment/", {"razorpay_order_id": "order_RZ1", "razorpay_payment_id": "pay_1",
                                                                         "razorpay_signature": sign(SECRET, "order_RZ1", "pay_1")}, format="json")
        self.assertTrue(ok.data["verified"], ok.data)
        self.assertEqual(Order.objects.get(pk=oid).payment_status, "paid")
        self.assertEqual(self.owner.get(f"/payments/receipt/{oid}/").data["total"], 200.0)

    def test_someone_else_cannot_pay_for_a_diners_order(self):
        oid = self.pickup(payment_method="online").data["id"]
        self.assertEqual(APIClient().post(f"/payments/orders/{oid}/create-payment/").status_code, 403)

    def test_partial_cash_refund_then_refuses_more_than_paid(self):
        oid = self.dinein().data["id"]
        self.owner.patch(f"/menu/api/orders/{oid}/", {"status": "completed"}, format="json")
        r = self.owner.post(f"/payments/orders/{oid}/refund/", {"amount": 100, "reason": "Cold food"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Order.objects.get(pk=oid).payment_status, "partially_refunded")
        self.assertEqual(self.owner.post(f"/payments/orders/{oid}/refund/", {"amount": 400}, format="json").status_code, 400)
        self.assertEqual(self.owner.post(f"/payments/orders/{oid}/refund/", {}, format="json").data["amount"], 360.0)
        self.assertEqual(Order.objects.get(pk=oid).payment_status, "refunded")

    def test_receipt_pdf_downloads(self):
        oid = self.dinein().data["id"]
        self.owner.patch(f"/menu/api/orders/{oid}/", {"status": "completed"}, format="json")
        r = self.owner.get(f"/payments/orders/{oid}/receipt/pdf/")
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))

    @mock.patch("payments.gateway.fetch_payment", return_value={"status": "captured", "amount": 20000})
    @mock.patch("payments.gateway.create_order", return_value={"id": "order_RZ2"})
    def test_reconciliation_settles_matching_payments(self, *_):
        oid = self.pickup(payment_method="online").data["id"]
        self.diner.post(f"/payments/orders/{oid}/create-payment/")
        self.diner.post(f"/payments/orders/{oid}/verify-payment/", {"razorpay_order_id": "order_RZ2", "razorpay_payment_id": "pay_2",
                                                                    "razorpay_signature": sign(SECRET, "order_RZ2", "pay_2")}, format="json")
        self.assertEqual(self.owner.post("/api/payments/reconciliation/run/").data["updated"], 1)
        summary = self.owner.get("/api/payments/reconciliation/").data["summary"]
        self.assertEqual((summary["settled"], summary["mismatch"]), (1, 0))
