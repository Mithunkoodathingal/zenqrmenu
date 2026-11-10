import csv
import io

from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from openpyxl import load_workbook
from rest_framework.test import APIClient

from analytics.models import ScheduledReport
from common.testing import make_menu, owner_client


class AnalyticsTests(TestCase):
    def setUp(self):
        self.owner, self.r = owner_client()
        self.item, _, self.table = make_menu(self.r)
        self.orders = [self.order(q) for q in (1, 2, 3)]
        self.owner.patch(f"/menu/api/orders/{self.orders[2]['id']}/", {"status": "cancelled"}, format="json")
        self.owner.patch(f"/menu/api/orders/{self.orders[0]['id']}/", {"status": "confirmed"}, format="json")

    def order(self, qty):
        return APIClient().post("/menu/api/orders/", {"table": self.table.id, "customer_phone": "98470000" + str(qty).zfill(2),
                                                      "items": [{"food_item_id": self.item.id, "quantity": qty}]}, format="json").data

    def test_dashboard_tiles(self):
        w = self.owner.get("/menu/api/dashboard/widgets/").data
        self.assertEqual((w["todays_orders"], w["live_orders"], w["kitchen_load"], w["todays_revenue"]), (3, 2, 1, 600.0))

    def test_cancelled_orders_are_left_out_of_revenue(self):
        s = self.owner.get("/menu/api/analytics/summary/").data
        self.assertEqual((s["revenue"], s["orders"], s["cancelled"], s["average_order_value"]), (600.0, 3, 1, 300.0))
        sales = self.owner.get("/menu/api/analytics/sales/").data
        self.assertEqual((sales["total"], len(sales["points"])), (600.0, 1))
        top = self.owner.get("/menu/api/analytics/top-items/").data
        self.assertEqual((top[0]["name"], top[0]["quantity"]), ("Chicken Biryani", 3))
        self.assertEqual(len(self.owner.get("/menu/api/analytics/heatmap/").data), 7 * 24)
        rev = self.owner.get("/menu/api/analytics/revenue/").data
        self.assertEqual(rev["by_payment_method"][0]["key"], "cash")
        for path in ("executive", "daily-sales", "monthly-sales", "payment-methods", "refunds", "menu", "top-customers",
                     "customers", "delivery", "kitchen", "coupons", "staff"):
            self.assertEqual(self.owner.get(f"/menu/api/analytics/{path}/").status_code, 200, path)

    def test_date_range_filters(self):
        s = self.owner.get("/menu/api/analytics/summary/", {"from": "2020-01-01", "to": "2020-01-31"}).data
        self.assertEqual(s["orders"], 0)

    def test_report_files(self):
        r = self.owner.post("/menu/api/reports/export/", {"type": "orders", "format": "csv"}, format="json")
        self.assertEqual(r["Content-Type"], "text/csv")
        rows = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig"))))
        self.assertEqual((rows[0][0], len(rows)), ("Order", 4))
        x = self.owner.post("/menu/api/reports/export/", {"type": "sales", "format": "xlsx"}, format="json")
        ws = load_workbook(io.BytesIO(x.content)).active
        self.assertEqual((ws["B2"].value, ws["E2"].value), (2, 600))
        p = self.owner.post("/menu/api/reports/export/", {"type": "menu", "format": "pdf"}, format="json")
        self.assertTrue(p.content.startswith(b"%PDF"))
        self.assertEqual(self.owner.post("/menu/api/reports/export/", {"type": "secrets", "format": "csv"}, format="json").status_code, 400)
        other, _ = owner_client("other")
        rows = other.post("/menu/api/reports/export/", {"type": "orders", "format": "csv"}, format="json").content.decode("utf-8-sig")
        self.assertEqual(len(rows.strip().splitlines()), 1)  # header only: other restaurants' orders never leak

    def test_scheduled_reports_are_emailed_when_due(self):
        s = self.owner.post("/menu/api/reports/scheduled/", {"type": "orders", "format": "csv", "frequency": "daily",
                                                              "destination": "email", "email": "boss@malabar.test", "enabled": True}, format="json")
        self.assertEqual(s.status_code, 201, s.data)
        self.assertIsNotNone(s.data["next_run_at"])
        ScheduledReport.objects.update(next_run_at=timezone.now())
        mail.outbox.clear()
        call_command("send_scheduled_reports", stdout=io.StringIO())
        self.assertEqual((mail.outbox[0].to, len(mail.outbox[0].attachments)), (["boss@malabar.test"], 1))
        self.assertGreater(ScheduledReport.objects.get().next_run_at, timezone.now())
        self.owner.patch(f"/menu/api/reports/scheduled/{s.data['id']}/", {"enabled": False}, format="json")
        self.assertFalse(self.owner.get("/menu/api/reports/scheduled/").data[0]["enabled"])
        self.assertEqual(self.owner.delete(f"/menu/api/reports/scheduled/{s.data['id']}/").status_code, 204)
