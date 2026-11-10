"""Every request the website makes for the features built so far must reach a view that accepts that method.

Collected from the React app. A 404 from a placeholder id is fine; an unknown URL or a 405 means the
server and the website disagree. Later stages append their calls here.
"""
from django.test import TestCase
from django.urls import Resolver404, resolve

from common.testing import make_customer, owner_client

CALLS = """
POST /api/register/
POST /api/login/
POST /api/logout/
GET /api/user/
GET /api/auth/user/
POST /api/auth/refresh/
POST /api/auth/google/
POST /api/password/reset/
POST /api/password/reset/confirm/
POST /api/resend-verification/
GET /menu/api/restaurant/
POST /menu/api/restaurant/
PUT /menu/api/restaurant/
PATCH /menu/api/restaurant/
GET /menu/api/restaurant/location/
PUT /menu/api/restaurant/location/
GET /menu/api/restaurant/delivery-zone/
PUT /menu/api/restaurant/delivery-zone/
GET /menu/api/restaurant/working-hours/
PUT /menu/api/restaurant/working-hours/
GET /menu/api/restaurant/settings/
PUT /menu/api/restaurant/settings/
GET /api/public/restaurants/1/
GET /api/public/restaurants/nearby/
GET /menu/api/restaurants/nearby/
POST /menu/api/delivery/quote/
GET /menu/api/search/
GET /api/branches/
POST /api/branches/
PATCH /api/branches/1/
DELETE /api/branches/1/
GET /api/branches/1/menu-overrides/
PUT /api/branches/1/menu-overrides/
GET /api/branches/1/category-overrides/
PUT /api/branches/1/category-overrides/
GET /menu/api/categories/
POST /menu/api/categories/
PATCH /menu/api/categories/1/
DELETE /menu/api/categories/1/
GET /menu/api/items/
POST /menu/api/items/
PATCH /menu/api/items/1/
PUT /menu/api/items/1/
DELETE /menu/api/items/1/
GET /menu/api/tables/
POST /menu/api/tables/
DELETE /menu/api/tables/1/
GET /menu/api/table/1/
GET /menu/api/qr/table/1/
GET /menu/api/qr/pickup/
GET /menu/api/qr/delivery/
POST /api/ai-import/extract/
GET /api/ai-import/image-search/
GET /subscription/api/plans/
GET /subscription/api/current/
GET /subscription/api/subscription/
GET /subscription/api/usage/
GET /subscription/api/invoices/
POST /subscription/api/create/
POST /subscription/api/upgrade/
POST /subscription/api/verify/
POST /subscription/api/cancel/
POST /api/customers/auth/email/request-otp/
POST /api/customers/auth/email/verify-otp/
GET /api/coupons/
POST /api/coupons/
PATCH /api/coupons/1/
DELETE /api/coupons/1/
POST /api/restaurants/1/coupons/validate/
GET /api/public/restaurants/1/offers/
POST /menu/api/orders/
GET /menu/api/orders/
GET /menu/api/orders/1/
PATCH /menu/api/orders/1/
DELETE /menu/api/orders/1/
GET /menu/api/orders/1/public/
GET /menu/api/table/1/orders/
POST /payments/orders/1/generate-otp/
POST /payments/orders/1/verify-otp/
POST /payments/orders/1/complete/
GET /payments/api/payment-settings/
POST /payments/api/payment-settings/
PUT /payments/api/payment-settings/
POST /payments/api/payment-settings/verify/
GET /api/payment-settings/incentive/
PUT /api/payment-settings/incentive/
GET /api/branches/payment-accounts/
PUT /api/branches/1/payment-account/
POST /api/branches/1/payment-account/verify/
POST /payments/orders/1/create-payment/
POST /payments/orders/1/verify-payment/
GET /payments/payments/history/
GET /payments/payments/1/
POST /payments/orders/1/refund/
GET /payments/orders/1/refund-status/
GET /payments/receipt/1/
GET /payments/orders/1/receipt/pdf/
POST /payments/orders/1/receipt/email/
POST /payments/orders/1/receipt/whatsapp/
GET /api/payments/reconciliation/
POST /api/payments/reconciliation/run/
POST /api/payments/reconciliation/1/resolve/
GET /menu/api/inventory/ingredients/
POST /menu/api/inventory/ingredients/
PATCH /menu/api/inventory/ingredients/1/
DELETE /menu/api/inventory/ingredients/1/
POST /menu/api/inventory/ingredients/1/adjust/
POST /menu/api/inventory/ingredients/1/purchase/
GET /menu/api/inventory/history/
GET /menu/api/inventory/purchases/
GET /menu/api/inventory/reservations/
GET /api/recipes/
PUT /api/recipes/1/
DELETE /api/recipes/1/
GET /api/staff/
POST /api/staff/create/
GET /api/staff/1/
PUT /api/staff/1/update/
DELETE /api/staff/1/delete/
PATCH /api/staff/1/shift/
PATCH /api/staff/1/shift-schedule/
PATCH /staff/attendance/1/
POST /staff/break/start/
POST /staff/break/end/
PATCH /api/staff/1/role/
GET /api/staff/me/
GET /staff/attendance/
POST /staff/attendance/clock-in/
POST /staff/attendance/clock-out/
GET /staff/breaks/
GET /api/delivery-partners/
POST /api/delivery-partners/
GET /api/delivery-partners/1/
PATCH /api/delivery-partners/1/
DELETE /api/delivery-partners/1/
POST /api/delivery-partners/1/availability/
POST /api/delivery-partners/1/location/
POST /api/orders/1/assign-partner/
POST /api/orders/1/unassign-partner/
GET /api/delivery/my-assignments/
POST /api/delivery/assignments/1/start/
POST /api/delivery/assignments/1/delivered/
POST /api/delivery/assignments/1/location/
GET /kds/orders/
PATCH /kds/orders/1/status/
PATCH /kds/orders/1/priority/
POST /kds/orders/1/notes/
GET /kds/statistics/
GET /kitchen/notes/
POST /kitchen/notes/
PATCH /kitchen/notes/1/
DELETE /kitchen/notes/1/
GET /menu/api/notifications/
POST /menu/api/notifications/1/read/
POST /menu/api/notifications/read-all/
GET /menu/api/notifications/preferences/
PATCH /menu/api/notifications/preferences/
POST /menu/api/notifications/test/
GET /api/restaurants/1/reviews/
GET /api/reviews/
PATCH /api/reviews/1/
GET /api/marketing/customers/
GET /api/marketing/campaigns/
POST /api/marketing/campaigns/preview/
POST /api/marketing/campaigns/
PATCH /api/marketing/campaigns/1/
DELETE /api/marketing/campaigns/1/
POST /api/marketing/campaigns/1/send/
GET /api/marketing/unsubscribe-link/a%40b.com/
GET /api/marketing/unsubscribe/abc/
POST /api/marketing/unsubscribe/abc/
GET /menu/api/dashboard/widgets/
GET /menu/api/analytics/executive/
GET /menu/api/analytics/summary/
GET /menu/api/analytics/sales/
GET /menu/api/analytics/daily-sales/
GET /menu/api/analytics/monthly-sales/
GET /menu/api/analytics/heatmap/
GET /menu/api/analytics/revenue/
GET /menu/api/analytics/payment-methods/
GET /menu/api/analytics/refunds/
GET /menu/api/analytics/menu/
GET /menu/api/analytics/top-customers/
GET /menu/api/analytics/top-items/
GET /menu/api/analytics/customers/
GET /menu/api/analytics/delivery/
GET /menu/api/analytics/kitchen/
GET /menu/api/analytics/coupons/
GET /menu/api/analytics/staff/
POST /menu/api/reports/export/
GET /menu/api/reports/scheduled/
POST /menu/api/reports/scheduled/
PATCH /menu/api/reports/scheduled/1/
DELETE /menu/api/reports/scheduled/1/
"""

# Diner-only calls, made with a diner's token.
CUSTOMER_CALLS = """
GET /api/customers/me/
PATCH /api/customers/me/
GET /api/customers/me/orders/
GET /api/customers/me/orders/1/
GET /api/customers/me/addresses/
POST /api/customers/me/addresses/
PATCH /api/customers/me/addresses/1/
DELETE /api/customers/me/addresses/1/
POST /api/customers/me/addresses/1/set-default/
GET /api/customers/me/orders/1/review-eligibility/
POST /api/customers/me/orders/1/review/
GET /api/customers/me/reviews/
PATCH /api/customers/me/reviews/1/
DELETE /api/customers/me/reviews/1/
POST /api/marketing/consent/
"""


class FrontendContractTests(TestCase):
    def test_every_frontend_call_reaches_a_view(self):
        self.assertEqual(self._problems(owner_client()[0], CALLS), [])

    def test_every_diner_call_reaches_a_view(self):
        self.assertEqual(self._problems(make_customer()[0], CUSTOMER_CALLS), [])

    def _problems(self, client, calls):
        problems = []
        for line in calls.strip().splitlines():
            method, path = line.split()
            try:
                resolve(path)
            except Resolver404:
                problems.append(f"{method} {path}: no URL")
                continue
            response = getattr(client, method.lower())(path, {}, format="json")
            if response.status_code == 405:
                problems.append(f"{method} {path}: method not allowed")
            # 503 = an outside service (Google, Gemini, image search) isn't configured in tests.
            if response.status_code >= 500 and response.status_code != 503:
                problems.append(f"{method} {path}: server error {response.status_code}")
        return problems
