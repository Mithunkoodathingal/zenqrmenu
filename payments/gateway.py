"""The only place that talks to Razorpay. Amounts are in paise. Checks replace these functions with fakes."""
import hashlib
import hmac

import requests

API = "https://api.razorpay.com/v1"
TIMEOUT = 20


class GatewayError(Exception):
    """Razorpay refused the request or couldn't be reached."""


def _call(method, path, key, secret, **kwargs):
    try:
        res = requests.request(method, f"{API}{path}", auth=(key, secret), timeout=TIMEOUT, **kwargs)
    except requests.RequestException as e:
        raise GatewayError("Couldn't reach Razorpay. Try again in a moment.") from e
    if res.status_code == 401:
        raise GatewayError("Razorpay rejected these keys.")
    if res.status_code >= 400:
        try:
            msg = res.json().get("error", {}).get("description")
        except ValueError:
            msg = None
        raise GatewayError(msg or f"Razorpay error ({res.status_code}).")
    return res.json()


def check_credentials(key, secret):
    """True when Razorpay accepts the key pair."""
    try:
        _call("GET", "/payments", key, secret, params={"count": 1})
        return True
    except GatewayError as e:
        if "rejected" in str(e):
            return False
        raise


def create_order(key, secret, amount_paise, receipt, notes=None, currency="INR"):
    return _call("POST", "/orders", key, secret,
                 json={"amount": amount_paise, "currency": currency, "receipt": receipt[:40], "notes": notes or {}})


def fetch_payment(key, secret, payment_id):
    return _call("GET", f"/payments/{payment_id}", key, secret)


def refund(key, secret, payment_id, amount_paise, notes=None):
    return _call("POST", f"/payments/{payment_id}/refund", key, secret, json={"amount": amount_paise, "notes": notes or {}})


def signature_ok(secret, razorpay_order_id, razorpay_payment_id, signature):
    expected = hmac.new(secret.encode(), f"{razorpay_order_id}|{razorpay_payment_id}".encode(), hashlib.sha256).hexdigest()
    return bool(signature) and hmac.compare_digest(expected, str(signature))


def webhook_ok(secret, body, signature):
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return bool(secret and signature) and hmac.compare_digest(expected, str(signature))
