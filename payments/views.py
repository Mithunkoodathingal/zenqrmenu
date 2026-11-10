"""Payment settings, branch accounts, online payment for orders, history, refunds, receipts and reconciliation."""
import io
import json
import logging
import re
from decimal import Decimal

from django.db import transaction
from django.db.models import F, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.auth import OptionalJWTAuthentication, customer_of
from common.email import send_email
from common.geo import money
from common.permissions import IsOwnerOrRole
from common.tenancy import get_restaurant, require_owner
from orders.models import Order
from restaurants.models import Branch

from . import gateway
from .models import BranchPaymentAccount, Payment, PaymentAudit, PaymentIncentive, PaymentSettings, Receipt, Refund
from .routing import route, routes_to, secret_for_key
from .services import audit, ensure_receipt, mark_paid, settings_for

log = logging.getLogger(__name__)
KEY = re.compile(r"^rzp_(test|live)_[A-Za-z0-9]{6,}$")
MONEY_ROLES = ["manager", "cashier"]


def _bool(v):
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


# ─── Parent account settings ──────────────────────────────────────────────

def settings_out(s):
    return {"razorpay_key_id": s.razorpay_key_id, "has_key_secret": bool(s.key_secret_enc),
            "has_webhook_secret": bool(s.webhook_secret_enc), "accept_online": s.accept_online,
            "accept_cash_pickup": s.accept_cash_pickup, "accept_cash_delivery": s.accept_cash_delivery,
            "is_active": s.is_active, "environment": s.environment, "currency": s.currency, "verified": s.verified,
            "verified_at": s.verified_at, "merchant_name": s.merchant_name or None, "merchant_email": s.merchant_email or None,
            "last_payment_received_at": s.last_payment_received_at, "created_at": s.created_at, "updated_at": s.updated_at}


class SettingsView(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ["manager"]

    def get(self, request):
        r = get_restaurant(request, required=False)
        if r is None:
            return Response(settings_out(PaymentSettings()))
        return Response(settings_out(settings_for(r)))

    def post(self, request):
        r = require_owner(request)
        s = settings_for(r)
        d = request.data
        if "razorpay_key_id" in d:
            key = str(d.get("razorpay_key_id") or "").strip()
            if key and not KEY.match(key):
                raise ValidationError({"razorpay_key_id": ["Key ID looks like rzp_live_XXXXXXXX or rzp_test_XXXXXXXX."]})
            if key != s.razorpay_key_id:
                s.razorpay_key_id, s.verified, s.verified_at, s.merchant_name = key, False, None, ""
        if d.get("razorpay_key_secret"):
            s.key_secret = str(d["razorpay_key_secret"]).strip()
            s.verified, s.verified_at = False, None
        if d.get("webhook_secret"):
            s.webhook_secret = str(d["webhook_secret"]).strip()
        for f in ("accept_online", "accept_cash_pickup", "accept_cash_delivery", "is_active"):
            if f in d:
                setattr(s, f, _bool(d[f]))
        if "accept_online_payment" in d:
            s.accept_online = _bool(d["accept_online_payment"])
        if d.get("environment") in ("test", "live"):
            s.environment = d["environment"]
        if s.razorpay_key_id and s.environment not in s.razorpay_key_id:
            raise ValidationError({"environment": [f"This key is a {'test' if '_test_' in s.razorpay_key_id else 'live'} key; switch the environment to match."]})
        if d.get("currency"):
            s.currency = str(d["currency"]).upper()[:3]
        if s.accept_online and not (s.razorpay_key_id and s.key_secret_enc):
            raise ValidationError({"accept_online": ["Save your Razorpay Key ID and Secret before turning on online payment."]})
        s.save()
        return Response(settings_out(s))

    put = post
    patch = post


@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def verify_settings(request):
    r = require_owner(request)
    s = settings_for(r)
    if not (s.razorpay_key_id and s.key_secret):
        return Response({"verified": False, "message": "Save your Key ID and Key Secret first."}, status=400)
    try:
        ok = gateway.check_credentials(s.razorpay_key_id, s.key_secret)
    except gateway.GatewayError as e:
        return Response({"detail": str(e)}, status=502)
    if not ok:
        s.verified = False
        s.save(update_fields=["verified", "updated_at"])
        return Response({"verified": False, "message": "Razorpay rejected the saved credentials."}, status=400)
    s.verified, s.verified_at = True, timezone.now()
    s.merchant_name = s.merchant_name or r.name
    s.save()
    return Response({"success": True, "verified": True, "merchant_name": s.merchant_name, "merchant_email": s.merchant_email or None,
                     "message": "Razorpay accepted these keys."})


class IncentiveView(APIView):
    permission_classes = [IsOwnerOrRole]
    allowed_roles = ["manager"]

    @staticmethod
    def _out(i):
        return {"enabled": i.enabled, "type": i.type, "value": float(i.value),
                "max_discount": float(i.max_discount) if i.max_discount is not None else None,
                "min_order": float(i.min_order) if i.min_order is not None else None,
                "order_types": i.order_types or ["dine_in", "pickup", "delivery"]}

    def get(self, request):
        r = get_restaurant(request, required=False)
        i = (PaymentIncentive.objects.filter(restaurant=r).first() if r else None) or PaymentIncentive()
        return Response(self._out(i))

    def put(self, request):
        r = require_owner(request)
        i = PaymentIncentive.objects.filter(restaurant=r).first() or PaymentIncentive(restaurant=r)
        d = request.data
        i.enabled = _bool(d.get("enabled", i.enabled))
        if d.get("type", i.type) not in ("percent", "fixed"):
            raise ValidationError({"type": ["Pick percent or fixed."]})
        i.type = d.get("type", i.type)
        try:
            i.value = money(d.get("value", i.value) or 0)
            i.max_discount = money(d["max_discount"]) if d.get("max_discount") not in (None, "") else None
            i.min_order = money(d["min_order"]) if d.get("min_order") not in (None, "") else None
        except Exception:
            raise ValidationError({"value": ["Enter numbers only."]})
        if i.value < 0 or (i.type == "percent" and i.value > 50):
            raise ValidationError({"value": ["Use a percent between 0 and 50."]})
        types = d.get("order_types", i.order_types) or []
        if not isinstance(types, list) or any(t not in ("dine_in", "dinein", "pickup", "delivery") for t in types):
            raise ValidationError({"order_types": ["Pick dine-in, pickup and/or delivery."]})
        i.order_types = types
        i.save()
        return Response(self._out(i))

    patch = put


# ─── Branch accounts ──────────────────────────────────────────────────────

def account_out(branch):
    a = BranchPaymentAccount.objects.filter(branch=branch).first() or BranchPaymentAccount(branch=branch)
    return {"branch_id": branch.id, "branch_name": branch.name, "mode": a.mode, "razorpay_key_id": a.razorpay_key_id,
            "has_key_secret": bool(a.key_secret_enc), "verified": a.verified, "verified_at": a.verified_at,
            "merchant_name": a.merchant_name or None, "environment": a.environment, "routes_to": routes_to(branch)}


@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def branch_accounts(request):
    r = get_restaurant(request, required=False)
    if r is None:
        return Response([])
    r.main_branch()
    return Response([account_out(b) for b in r.branches.all()])


@api_view(["PUT", "PATCH"])
@permission_classes([IsOwnerOrRole])
def branch_account(request, pk):
    r = require_owner(request)
    b = get_object_or_404(Branch, pk=pk, restaurant=r)
    a = BranchPaymentAccount.objects.filter(branch=b).first() or BranchPaymentAccount(branch=b)
    d = request.data
    if d.get("mode") == "inherit":
        a.mode = "inherit"
        a.save()
        return Response(account_out(b))
    if d.get("mode") not in ("own", None):
        raise ValidationError({"mode": ["Pick inherit or own."]})
    key = str(d.get("razorpay_key_id") or a.razorpay_key_id).strip()
    if not key:
        raise ValidationError({"razorpay_key_id": ["Enter the branch's Razorpay Key ID."]})
    if not KEY.match(key):
        raise ValidationError({"razorpay_key_id": ["Key ID looks like rzp_live_XXXXXXXX or rzp_test_XXXXXXXX."]})
    if key != a.razorpay_key_id or d.get("razorpay_key_secret"):
        a.verified, a.verified_at, a.merchant_name = False, None, ""
    a.mode, a.razorpay_key_id = "own", key
    a.environment = "live" if d.get("environment") == "live" else ("test" if d.get("environment") == "test" else a.environment)
    if d.get("razorpay_key_secret"):
        a.key_secret = str(d["razorpay_key_secret"]).strip()
    if not a.key_secret_enc:
        raise ValidationError({"razorpay_key_secret": ["Enter the Key Secret."]})
    a.save()
    return Response(account_out(b))


@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def verify_branch_account(request, pk):
    r = require_owner(request)
    b = get_object_or_404(Branch, pk=pk, restaurant=r)
    a = BranchPaymentAccount.objects.filter(branch=b).first()
    if a is None or a.mode != "own":
        raise ValidationError({"detail": "This branch uses the parent account — nothing to verify."})
    try:
        ok = gateway.check_credentials(a.razorpay_key_id, a.key_secret)
    except gateway.GatewayError as e:
        return Response({"detail": str(e)}, status=502)
    if not ok:
        a.verified = False
        a.save()
        return Response({"verified": False, "message": "Razorpay rejected this branch's keys. Payments keep going to the parent account."}, status=400)
    a.verified, a.verified_at, a.merchant_name = True, timezone.now(), a.merchant_name or f"{b.name} account"
    a.save()
    return Response({**account_out(b), "verified": True, "message": "Verified. This branch's online payments now go to its own account."})


# ─── Paying for an order ──────────────────────────────────────────────────

def _payable_order(request, pk):
    o = get_object_or_404(Order.objects.select_related("restaurant", "branch"), pk=pk, deleted_at__isnull=True)
    me = customer_of(request)
    if o.customer_id and (me is None or me.id != o.customer_id):
        raise PermissionDenied("Sign in with the account that placed this order to pay for it.")
    if o.payment_method != Order.PaymentMethod.ONLINE:
        raise ValidationError({"detail": "This order is paid in cash."})
    if o.status == Order.Status.CANCELLED:
        raise ValidationError({"detail": "This order was cancelled."})
    return o


@api_view(["POST"])
@authentication_classes([OptionalJWTAuthentication])
@permission_classes([AllowAny])
def create_payment(request, pk):
    o = _payable_order(request, pk)
    if o.payment_status == Order.PaymentStatus.PAID:
        raise ValidationError({"detail": "This order is already paid."})
    key, secret, _, source = route(o.branch)
    if not (key and secret):
        raise ValidationError({"detail": "Online payment isn't available at this restaurant right now."})
    amount_paise = int((o.total * 100).quantize(Decimal("1")))
    p = o.payments.filter(status=Payment.Status.CREATED, account_key_id=key, amount=o.total).exclude(razorpay_order_id="").first()
    if p is None:
        try:
            rz = gateway.create_order(key, secret, amount_paise, o.order_number,
                                      {"order_id": str(o.id), "restaurant_id": str(o.restaurant_id)}, settings_for(o.restaurant).currency)
        except gateway.GatewayError as e:
            return Response({"detail": str(e)}, status=502)
        p = Payment.objects.create(restaurant=o.restaurant, branch=o.branch, order=o, amount=o.total,
                                   razorpay_order_id=rz["id"], account_key_id=key, account_source=source,
                                   customer_name=o.customer_name, currency=settings_for(o.restaurant).currency)
        audit("created", f"Payment of ₹{o.total} started", p)
    return Response({"transaction_id": p.transaction_id, "razorpay_order_id": p.razorpay_order_id, "order_id": p.razorpay_order_id,
                     "amount": amount_paise, "currency": p.currency, "key": key, "razorpay_key": key})


@api_view(["POST"])
@authentication_classes([OptionalJWTAuthentication])
@permission_classes([AllowAny])
def verify_payment(request, pk):
    o = _payable_order(request, pk)
    d = request.data
    p = Payment.objects.filter(order=o, razorpay_order_id=str(d.get("razorpay_order_id") or "")).order_by("-id").first()
    if p is None:
        raise ValidationError({"detail": "This payment doesn't belong to this order."})
    if p.status == Payment.Status.CAPTURED:
        return Response({"success": True, "verified": True, "message": "Payment already confirmed."})
    secret = secret_for_key(o.restaurant, p.account_key_id)
    if not gateway.signature_ok(secret, p.razorpay_order_id, str(d.get("razorpay_payment_id") or ""), d.get("razorpay_signature")):
        # Leave the payment open: a forged callback must not cancel a real payment in progress.
        audit("signature_mismatch", "Payment confirmation had an invalid signature", p)
        return Response({"success": False, "verified": False, "detail": "We couldn't confirm this payment."}, status=400)
    with transaction.atomic():
        p.razorpay_payment_id = str(d["razorpay_payment_id"])
        mark_paid(o, p, "diner")
    return Response({"success": True, "verified": True, "message": "Payment confirmed."})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def webhook(request):
    """Razorpay webhook (payment.captured / payment.failed / refund.processed), checked with the restaurant's webhook secret."""
    try:
        body = json.loads(request.body or b"{}")
        entity = body["payload"]["payment"]["entity"] if "payment" in body.get("payload", {}) else body["payload"]["refund"]["entity"]
    except (ValueError, KeyError, TypeError):
        return Response({"detail": "Bad payload"}, status=400)
    rz_order = entity.get("order_id") or ""
    p = Payment.objects.select_related("order", "restaurant").filter(
        Q(razorpay_order_id=rz_order) | Q(razorpay_payment_id=entity.get("payment_id") or entity.get("id") or "-")).first()
    if p is None:
        return Response({"ok": True})
    secret = settings_for(p.restaurant).webhook_secret
    if not gateway.webhook_ok(secret, request.body, request.headers.get("X-Razorpay-Signature")):
        return Response({"detail": "Bad signature"}, status=400)
    event = body.get("event")
    if event == "payment.captured" and p.status != Payment.Status.CAPTURED:
        p.razorpay_payment_id = entity.get("id", p.razorpay_payment_id)
        p.method = entity.get("method", "")
        mark_paid(p.order, p, "razorpay webhook")
    elif event == "payment.failed" and p.status == Payment.Status.CREATED:
        p.status = Payment.Status.FAILED
        p.save(update_fields=["status", "updated_at"])
        _alert("payment_failed", p.order, entity.get("error_description") or "")
    elif event == "refund.processed":
        Refund.objects.filter(gateway_refund_id=entity.get("id")).update(status="processed")
    return Response({"ok": True})


def _alert(kind, order, *args):
    from django.apps import apps as django_apps
    if django_apps.is_installed("notifications"):
        from notifications import hooks
        getattr(hooks, kind)(order, *args)


# ─── History, detail, refunds ─────────────────────────────────────────────

def payment_out(p):
    receipt = Receipt.objects.filter(order_id=p.order_id).first()
    return {"id": p.id, "order": p.order_id, "order_id": p.order_id, "order_number": p.order.order_number,
            "transaction_id": p.transaction_id, "amount": float(p.amount), "refunded_amount": float(p.refunded_amount),
            "currency": p.currency, "status": p.status, "gateway": p.gateway, "method": p.method or p.gateway,
            "customer_name": p.customer_name, "created_at": p.created_at, "captured_at": p.captured_at,
            "razorpay_order_id": p.razorpay_order_id, "razorpay_payment_id": p.razorpay_payment_id,
            "gateway_payment_id": p.razorpay_payment_id, "branch_name": p.branch.name, "account": p.account_key_id,
            "settlement_status": p.settlement_status, "receipt": receipt.invoice_number if receipt else None}


def refund_out(f):
    return {"id": f.id, "payment": f.payment_id, "amount": float(f.amount), "reason": f.reason, "status": f.status,
            "gateway_refund_id": f.gateway_refund_id, "created_at": f.created_at}


def receipt_out(rc):
    o = rc.order
    return {"id": rc.id, "order": o.id, "order_id": o.id, "order_number": o.order_number, "receipt_number": rc.invoice_number,
            "invoice_number": rc.invoice_number, "invoice_date": rc.generated_at, "generated_at": rc.generated_at,
            "created_at": rc.generated_at, "customer_name": o.customer_name, "customer_email": o.customer_email,
            "total": float(o.total), "currency": o.restaurant.currency, "printed": rc.printed,
            "download_count": rc.download_count, "email_status": rc.email_status, "whatsapp_status": rc.whatsapp_status,
            "payment_method": o.payment_method,
            "items": [{"name": i.name, "quantity": i.quantity, "price": float(i.unit_price), "total": float(i.line_total)} for i in o.items.all()],
            "subtotal": float(o.subtotal), "discount_amount": float(o.discount_amount + o.online_discount),
            "tax_amount": float(o.tax_amount), "delivery_charge": float(o.delivery_charge), "tip_amount": float(o.tip_amount)}


def _payments(request):
    r = get_restaurant(request)
    return Payment.objects.filter(restaurant=r).select_related("order", "branch")


@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def history(request):
    if get_restaurant(request, required=False) is None:
        return Response({"success": True, "count": 0, "payments": []})
    qs = _payments(request)
    q = request.query_params
    status = q.get("status")
    if status == "paid":
        qs = qs.filter(status__in=[Payment.Status.CAPTURED, Payment.Status.PARTIALLY_REFUNDED, Payment.Status.REFUNDED])
    elif status:
        qs = qs.filter(status=status)
    if q.get("gateway"):
        qs = qs.filter(gateway=q["gateway"])
    if q.get("method"):
        qs = qs.filter(Q(method=q["method"]) | Q(gateway=q["method"]))
    if q.get("customer"):
        qs = qs.filter(customer_name__icontains=q["customer"])
    if parse_date(q.get("start_date") or ""):
        qs = qs.filter(created_at__date__gte=parse_date(q["start_date"]))
    if parse_date(q.get("end_date") or ""):
        qs = qs.filter(created_at__date__lte=parse_date(q["end_date"]))
    if q.get("branch") not in (None, "", "all"):
        qs = qs.filter(branch_id=q["branch"])
    rows = [payment_out(p) for p in qs[:500]]
    return Response({"success": True, "count": len(rows), "payments": rows})


@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def payment_detail(request, pk):
    p = get_object_or_404(_payments(request), pk=pk)
    receipt = Receipt.objects.filter(order_id=p.order_id).first()
    logs = PaymentAudit.objects.filter(Q(payment=p) | Q(order_id=p.order_id)).distinct()[:50]
    return Response({"payment": payment_out(p), "refunds": [refund_out(f) for f in p.refunds.all()],
                     "receipt": receipt_out(receipt) if receipt else None,
                     "audit_logs": [{"id": a.id, "action": a.action, "description": a.description, "user": a.user or None,
                                     "created_at": a.created_at} for a in logs]})


@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def create_refund(request, pk):
    r = get_restaurant(request)
    o = get_object_or_404(Order, pk=pk, restaurant=r)
    if request.user.id != r.owner_id:
        from common.tenancy import staff_membership
        m = staff_membership(request.user)
        if not m or m.role not in MONEY_ROLES:
            raise PermissionDenied("Only the owner, a manager or a cashier can refund.")
    with transaction.atomic():
        p = Payment.objects.select_for_update().filter(
            order=o, status__in=[Payment.Status.CAPTURED, Payment.Status.PARTIALLY_REFUNDED]).first()
        if p is None:
            raise ValidationError({"detail": "This order has no payment to refund."})
        left = p.amount - p.refunded_amount
        raw = request.data.get("amount")
        try:
            amount = money(raw) if raw not in (None, "") else left
        except Exception:
            raise ValidationError({"amount": ["Enter a valid amount."]})
        if not (Decimal("0") < amount <= left):
            raise ValidationError({"amount": [f"You can refund up to ₹{left}."]})
        reason = str(request.data.get("reason") or "")[:255]
        f = Refund(payment=p, amount=amount, reason=reason, created_by=request.user.username)
        if p.gateway == "razorpay":
            secret = secret_for_key(r, p.account_key_id)
            try:
                rz = gateway.refund(p.account_key_id, secret, p.razorpay_payment_id, int(amount * 100), {"reason": reason})
            except gateway.GatewayError as e:
                return Response({"detail": str(e)}, status=502)
            f.gateway_refund_id = rz.get("id", "")
            f.status = "processed" if rz.get("status") == "processed" else "pending"
        else:
            f.status = "processed"  # cash handed back at the counter
        f.save()
        p.refunded_amount += amount
        p.status = Payment.Status.REFUNDED if p.refunded_amount >= p.amount else Payment.Status.PARTIALLY_REFUNDED
        p.save()
        o.payment_status = Order.PaymentStatus.REFUNDED if p.status == Payment.Status.REFUNDED else Order.PaymentStatus.PARTIALLY_REFUNDED
        o.save(update_fields=["payment_status", "updated_at"])
        audit("refund", f"Refund of ₹{amount} ({f.status})" + (f": {reason}" if reason else ""), p, user=request.user.username)
        if f.status == "processed":
            _alert("refund_completed", o, amount)
    return Response(refund_out(f), status=201)


@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def refund_status(request, pk):
    o = get_object_or_404(Order, pk=pk, restaurant=get_restaurant(request))
    refunds = Refund.objects.filter(payment__order=o)
    return Response({"order_id": o.id, "payment_status": o.payment_status, "refunds": [refund_out(f) for f in refunds]})


# ─── Receipts ─────────────────────────────────────────────────────────────

def _receipt(request, order_id):
    o = get_object_or_404(Order.objects.select_related("restaurant"), pk=order_id, restaurant=get_restaurant(request))
    if o.payment_status not in (Order.PaymentStatus.PAID, Order.PaymentStatus.PARTIALLY_REFUNDED, Order.PaymentStatus.REFUNDED):
        raise ValidationError({"detail": "A receipt is created once the order is paid."})
    return ensure_receipt(o)


@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def receipt(request, order_id):
    return Response(receipt_out(_receipt(request, order_id)))


def receipt_pdf_bytes(rc):
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    o, r = rc.order, rc.order.restaurant
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A5)
    w, h = A5
    y = h - 18 * mm

    def line(text, size=10, bold=False, right=None):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(14 * mm, y, text)
        if right is not None:
            c.drawRightString(w - 14 * mm, y, right)
        y -= size * 0.5 * mm + 3 * mm

    line(r.name, 15, True)
    if r.address:
        line(r.address[:80], 8)
    if r.phone:
        line(f"Phone: {r.phone}", 8)
    y -= 2 * mm
    line(f"Receipt {rc.invoice_number}", 11, True)
    line(f"Order {o.order_number} · {timezone.localtime(o.created_at).strftime('%d %b %Y, %I:%M %p')}", 8)
    if o.customer_name:
        line(f"Customer: {o.customer_name}", 8)
    y -= 2 * mm
    rs = "Rs. "
    for i in o.items.all():
        line(f"{i.quantity} x {i.name}"[:48], 9, right=f"{rs}{i.line_total:.2f}")
    y -= 2 * mm
    line("Subtotal", 9, right=f"{rs}{o.subtotal:.2f}")
    if o.discount_amount:
        line(f"Coupon {o.coupon_code}", 9, right=f"-{rs}{o.discount_amount:.2f}")
    if o.online_discount:
        line("Online payment discount", 9, right=f"-{rs}{o.online_discount:.2f}")
    if o.tax_amount:
        line("Tax", 9, right=f"{rs}{o.tax_amount:.2f}")
    if o.delivery_charge:
        line("Delivery", 9, right=f"{rs}{o.delivery_charge:.2f}")
    if o.tip_amount:
        line("Tip", 9, right=f"{rs}{o.tip_amount:.2f}")
    line("Total", 11, True, right=f"{rs}{o.total:.2f}")
    line(f"Paid by {o.payment_method}", 8)
    footer = (r.settings or {}).get("footer_message") or "Thank you!"
    line(str(footer)[:80], 8)
    c.showPage()
    c.save()
    return buf.getvalue()


@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def receipt_pdf(request, order_id):
    rc = _receipt(request, order_id)
    Receipt.objects.filter(pk=rc.pk).update(download_count=F("download_count") + 1)
    res = HttpResponse(receipt_pdf_bytes(rc), content_type="application/pdf")
    res["Content-Disposition"] = f'attachment; filename="receipt-{rc.order.order_number}.pdf"'
    return res


@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def receipt_email(request, order_id):
    rc = _receipt(request, order_id)
    to = str(request.data.get("email") or rc.order.customer_email or "").strip()
    if not to or "@" not in to:
        raise ValidationError({"email": ["Enter the email to send the receipt to."]})
    o = rc.order
    lines = "\n".join(f"{i.quantity} x {i.name}: ₹{i.line_total}" for i in o.items.all())
    sent = send_email(to, f"Your receipt from {o.restaurant.name} ({rc.invoice_number})",
                      f"Thank you for ordering from {o.restaurant.name}.\n\nOrder {o.order_number}\n{lines}\n\n"
                      f"Total: ₹{o.total} (paid by {o.payment_method})\nReceipt {rc.invoice_number}")
    rc.email_status = "sent" if sent else "failed"
    rc.emailed_to = to
    rc.save(update_fields=["email_status", "emailed_to"])
    if not sent:
        return Response({"detail": "The email couldn't be sent right now. Try again shortly."}, status=503)
    return Response({"success": True, "message": f"Receipt emailed to {to}."})


@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def receipt_whatsapp(request, order_id):
    _receipt(request, order_id)
    return Response({"detail": "WhatsApp sending isn't connected yet. Email the receipt or download the PDF instead."}, status=501)


# ─── Reconciliation ───────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsOwnerOrRole])
def reconciliation(request):
    r = get_restaurant(request, required=False)
    if r is None:
        return Response({"rows": [], "summary": {"total": 0, "settled": 0, "pending": 0, "mismatch": 0, "by_account": []}})
    qs = Payment.objects.filter(restaurant=r, gateway="razorpay").exclude(status__in=[Payment.Status.CREATED, Payment.Status.FAILED]).select_related("order", "branch")
    if request.query_params.get("branch") not in (None, "", "all"):
        qs = qs.filter(branch_id=request.query_params["branch"])
    rows, by = [], {}
    for p in qs[:1000]:
        rows.append({"order_id": p.order_id, "order_number": p.order.order_number, "branch_id": p.branch_id, "branch_name": p.branch.name,
                     "amount": float(p.amount), "account": p.account_key_id, "expected_account": routes_to(p.branch)["key_id"],
                     "razorpay_payment_id": p.razorpay_payment_id, "settlement_status": p.settlement_status, "created_at": p.created_at})
        x = by.setdefault(p.account_key_id, {"account": p.account_key_id, "amount": 0.0, "count": 0})
        x["amount"] += float(p.amount)
        x["count"] += 1
    count = lambda s: sum(1 for row in rows if row["settlement_status"] == s)
    return Response({"rows": rows, "summary": {"total": round(sum(row["amount"] for row in rows), 2), "settled": count("settled"),
                                               "pending": count("pending"), "mismatch": count("mismatch"), "by_account": list(by.values())}})


@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def run_reconciliation(request):
    """Ask Razorpay about each pending online payment; mark it settled, or flag a mismatch (wrong amount, status or account)."""
    r = require_owner(request)
    updated = 0
    for p in Payment.objects.filter(restaurant=r, gateway="razorpay", settlement_status="pending").exclude(razorpay_payment_id="")[:200]:
        secret = secret_for_key(r, p.account_key_id)
        try:
            rz = gateway.fetch_payment(p.account_key_id, secret, p.razorpay_payment_id)
        except gateway.GatewayError:
            continue
        ok = rz.get("status") in ("captured", "refunded") and int(rz.get("amount", -1)) == int(p.amount * 100)
        p.settlement_status = "settled" if ok and p.account_key_id == routes_to(p.branch)["key_id"] else "mismatch"
        p.save(update_fields=["settlement_status", "updated_at"])
        updated += 1
    return Response({"updated": updated})


@api_view(["POST"])
@permission_classes([IsOwnerOrRole])
def resolve_reconciliation(request, order_id):
    r = require_owner(request)
    n = Payment.objects.filter(restaurant=r, order_id=order_id, gateway="razorpay").update(settlement_status="settled")
    if not n:
        raise ValidationError({"detail": "No online payment for this order."})
    audit("reconciled", "Marked as settled by the owner", order=Order.objects.get(pk=order_id), user=request.user.username)
    return Response({"success": True})


# Money screens are for the owner, managers and cashiers only.
def _limit_roles():
    from rest_framework.views import APIView as _Base
    for obj in list(globals().values()):
        cls = getattr(obj, "cls", obj)
        if isinstance(cls, type) and issubclass(cls, _Base) and IsOwnerOrRole in getattr(cls, "permission_classes", []) \
                and getattr(cls, "allowed_roles", None) is None:
            cls.allowed_roles = MONEY_ROLES


_limit_roles()
