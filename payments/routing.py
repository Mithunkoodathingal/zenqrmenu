"""Which Razorpay account a branch's online payments go to.

- "branch": the branch has its own account and it is verified
- "parent": the branch inherits the restaurant's account
- "parent_fallback": the branch chose its own account but it isn't verified yet, so the parent is used
"""
from .models import BranchPaymentAccount, PaymentSettings


def _parent(restaurant):
    return PaymentSettings.objects.filter(restaurant=restaurant).first()


def route(branch):
    """(key_id, secret, merchant, source) for the branch."""
    acct = BranchPaymentAccount.objects.filter(branch=branch).first()
    if acct and acct.mode == "own" and acct.verified and acct.key_secret:
        return acct.razorpay_key_id, acct.key_secret, acct.merchant_name or f"{branch.name} account", "branch"
    parent = _parent(branch.restaurant)
    source = "parent_fallback" if acct and acct.mode == "own" else "parent"
    if parent is None:
        return "", "", "", source
    return parent.razorpay_key_id, parent.key_secret, parent.merchant_name or "Restaurant account", source


def routes_to(branch):
    key, _, merchant, source = route(branch)
    return {"key_id": key, "merchant": merchant, "source": source}


def secret_for_key(restaurant, key_id):
    """Secret for whichever of the restaurant's accounts uses `key_id` (for checking payments made earlier)."""
    parent = _parent(restaurant)
    if parent and parent.razorpay_key_id == key_id:
        return parent.key_secret
    acct = BranchPaymentAccount.objects.filter(branch__restaurant=restaurant, razorpay_key_id=key_id).first()
    return acct.key_secret if acct else ""
