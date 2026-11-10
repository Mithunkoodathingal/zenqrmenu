# Zen QR Menu — server (rebuild)

A fresh Django server for the Zen QR Menu website, replacing the old one at the same address
(`api.zenqrmenu.com`). It starts with an empty database: owners sign up again.

It is delivered in stages. Each stage's ZIP contains everything from the earlier stages.

| Stage | What works |
|---|---|
| 1 | Owner sign-up with email confirmation, login, Google sign-in, password reset · restaurant profile, location, delivery zone, opening hours, settings · branches with per-branch menu prices and hidden items/categories · categories, menu items (original and selling price), add-ons · tables and QR codes · public table menu · nearby restaurants and delivery quotes · plans and plan limits · AI menu import |
| 2 | Diner accounts (email code), profile photo and marketing consent, saved addresses · orders for dine-in (guests allowed), pickup and delivery (signed-in diners only), scheduled times, utensils and tips · prices worked out on the server from the branch menu · coupons with audience rules · online-payment discount · Razorpay payments, restaurant and branch payment accounts with key checks, refunds, reconciliation · receipts (view, PDF, email) · pickup/delivery handover codes by email · paid subscriptions |
| 3 (this ZIP) | Inventory per branch (adjustments, purchases, history), recipes linked to menu items, stock reserved on confirm / used on complete / released on cancel · staff with roles, invite-to-login, photos, shifts, breaks and attendance · delivery partners with photos, manual assignment, rider trip screens, live location and tracking · kitchen display (finished orders stay 12 hours), priority and kitchen notes · dashboard alerts and email alerts · reviews (verified diners, one per completed order, 7-day edit, owner reply/hide, admin removal) · marketing emails with consent and unsubscribe · dashboard tiles, analytics, CSV/Excel/PDF reports and scheduled report emails |

This ZIP is the complete server: every request the website makes is answered.

## Run it on a server

```bash
python -m venv venv && . venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in the values, then load them into the environment
python manage.py migrate
python manage.py seed_plans   # starting plans; edit prices in /admin/
python manage.py createsuperuser
python manage.py collectstatic --noinput
gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 3
```

Run `python manage.py send_scheduled_reports` every hour (cron) to email scheduled reports.

Use PostgreSQL in production (`DATABASE_URL=postgres://...`).

## Checks

```bash
python manage.py test --settings=config.settings_test
```

Every rule the website relies on has a check, plus a list of every website request that must reach the server
(`common/tests/test_frontend_contract.py`).

## Environment

See `.env.example`. Required: `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`, `FRONTEND_URL`, `BACKEND_URL`,
`CORS_ALLOWED_ORIGINS`, and email (`EMAIL_HOST` etc.) so owners receive confirmation links and diners receive
sign-in and handover codes. `RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET` are the platform's own account, used only for
plan payments; each restaurant enters its own Razorpay keys in Payment Settings.
Optional: `GOOGLE_CLIENT_ID` (Google sign-in), `GEMINI_API_KEY` (AI menu import), `UNSPLASH_ACCESS_KEY` or
`PEXELS_API_KEY` (dish photos), S3/R2 settings for photo storage.

## Notes

- A restaurant appears in nearby search once it has a map location and at least one table (diners open menus through a table link).
- Starting plan prices are placeholders: Free ₹0 (1 table), Basic ₹299, Standard ₹599, Enterprise ₹1499 per 30 days. Change them in `/admin/`.
- Opening hours are stored as `monday: {is_open, open, close}` plus `holidays`; the website converts to its own shape.
- Diners sign in with a 6-digit email code (valid 10 minutes, 5 tries) and stay signed in for `CUSTOMER_SESSION_DAYS` (30). An email used for a restaurant login can't also be a diner account.
- The server ignores prices sent by the website and recalculates every order from the menu, coupon and settings.
- Tax is added only when the restaurant's settings contain `tax_enabled` and `tax_percentage`.
- Restaurant Razorpay keys are stored encrypted; "verify" checks them against Razorpay. A branch without verified keys takes payments into the main account.
- Sending receipts on WhatsApp answers "not available yet" (no WhatsApp provider is connected).
- When a pickup or delivery order is marked Ready, the diner is emailed a 4-digit handover code. Restaurants that set `require_handover_code` in settings must enter it to complete the order.
- Staff and delivery partners with an email get a "choose your password" link and then log in on the normal restaurant login page. Their role limits what the server allows (the website's menus are only a convenience). Removing them switches their login off.
- Staff roles: owner (full access), manager, chef, cashier, waiter, delivery manager, inventory manager. Only the restaurant owner adds, edits or removes staff.
- Riders are assigned by hand. A rider can start a trip once the kitchen marks it Ready; marking it delivered completes the order (cash is recorded as paid).
- Kitchen display keeps completed and cancelled orders for 12 hours; kitchen notes are archived, never erased.
- Reviews: diners can delete theirs any time; restaurants can reply or hide but not delete; platform admins remove reviews in `/admin/` ("removed by admin").
- Marketing consent is per diner account (not per restaurant): unsubscribing stops marketing from every restaurant; order emails continue. Campaigns only reach diners who ordered at that restaurant and agreed to marketing.
- WhatsApp and push alerts answer "not available yet" (no provider connected); email alerts work.
