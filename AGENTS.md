# Zen QR Menu server — rules

- Response shapes follow the React website's API clients, not REST taste; `common/tests/test_frontend_contract.py` lists every website request and must stay green. Why: the website is already built and must work unchanged.
- Every owner/staff request resolves its restaurant and branch through `common/tenancy.py`; never filter by an id taken from the request body alone. Why: one owner must never see another's data.
- `price` on a menu item is the amount charged; `original_price` is only the struck-through price. Why: the website, cart and checkout all charge `price`.
- Menus are shared per restaurant; branches only override availability, price and visibility (`BranchItemOverride`, `BranchCategoryOverride`). Why: product decision — one menu, per-branch differences.
- Opening hours are stored in the full-day shape (`monday: {is_open, open, close}`) and validated by `restaurants/services.py`. Why: the website converts to and from exactly this shape.
- Errors use the format in `common/exceptions.py` (`error` text plus field errors). Why: the website's error formatter reads it.
- Built in stages; each stage adds apps and their requests to the contract test. Why: limits lost work if the workspace resets.
- Diners are Django users with a `customers.CustomerProfile`; owner logins, Google sign-in and password reset skip those accounts, and `common/permissions.py` keeps diners out of owner tools. Why: one email must never act as both roles.
- Order totals come only from `orders/pricing.py` (branch menu prices, coupon, online-payment discount, delivery, tip, tax); request prices are ignored. Why: diners can't change what they pay.
- Restaurant payment secrets are encrypted with `common/crypto.py` and never returned; responses only say whether one is saved. Why: keys must not leak through the website.
- Order side effects (stock, payments, delivery, notifications) run through hooks in `orders/services.py` (`on_order_created`, `on_status_change`, `after_status_change`) and extra order fields through each app's `hooks.order_fields`. Why: the order status stays the single source of truth and apps stay decoupled.
- Function views set role limits with `view.cls.allowed_roles`; restaurant owners (and staff with role `owner`) bypass role lists, riders never pass `IsOwnerOrRole`. Why: role checks must be enforced on the server, not by website menus.
