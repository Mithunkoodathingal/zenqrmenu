"""Restaurant payment accounts, payments, refunds and receipts. Secrets are stored encrypted and never returned."""
import uuid

from django.db import models

from common.crypto import decrypt, encrypt
from restaurants.models import Branch, Restaurant


def new_transaction_id():
    return f"txn_{uuid.uuid4().hex[:20]}"


class PaymentSettings(models.Model):
    """The restaurant's own (parent) Razorpay account and which payment methods diners may use."""

    restaurant = models.OneToOneField(Restaurant, on_delete=models.CASCADE, related_name="payment_settings")
    razorpay_key_id = models.CharField(max_length=64, blank=True)
    key_secret_enc = models.TextField(blank=True)
    webhook_secret_enc = models.TextField(blank=True)
    accept_online = models.BooleanField(default=False)
    accept_cash_pickup = models.BooleanField(default=True)
    accept_cash_delivery = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    environment = models.CharField(max_length=4, default="live")
    currency = models.CharField(max_length=3, default="INR")
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    merchant_name = models.CharField(max_length=150, blank=True)
    merchant_email = models.EmailField(blank=True)
    last_payment_received_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def key_secret(self):
        return decrypt(self.key_secret_enc)

    @key_secret.setter
    def key_secret(self, value):
        self.key_secret_enc = encrypt(value)

    @property
    def webhook_secret(self):
        return decrypt(self.webhook_secret_enc)

    @webhook_secret.setter
    def webhook_secret(self, value):
        self.webhook_secret_enc = encrypt(value)


class PaymentIncentive(models.Model):
    """Optional discount for paying online instead of cash."""

    restaurant = models.OneToOneField(Restaurant, on_delete=models.CASCADE, related_name="payment_incentive")
    enabled = models.BooleanField(default=False)
    type = models.CharField(max_length=7, default="percent")  # percent | fixed
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_order = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    order_types = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class BranchPaymentAccount(models.Model):
    """A branch either uses the parent account ("inherit") or its own verified Razorpay account ("own")."""

    branch = models.OneToOneField(Branch, on_delete=models.CASCADE, related_name="payment_account")
    mode = models.CharField(max_length=7, default="inherit")
    razorpay_key_id = models.CharField(max_length=64, blank=True)
    key_secret_enc = models.TextField(blank=True)
    environment = models.CharField(max_length=4, default="test")
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    merchant_name = models.CharField(max_length=150, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def key_secret(self):
        return decrypt(self.key_secret_enc)

    @key_secret.setter
    def key_secret(self, value):
        self.key_secret_enc = encrypt(value)


class Payment(models.Model):
    class Status(models.TextChoices):
        CREATED = "created"
        CAPTURED = "captured"
        FAILED = "failed"
        PARTIALLY_REFUNDED = "partially_refunded"
        REFUNDED = "refunded"

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="payments")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="payments")
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="payments")
    transaction_id = models.CharField(max_length=40, unique=True, default=new_transaction_id)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    refunded_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="INR")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED, db_index=True)
    gateway = models.CharField(max_length=10, default="razorpay")  # razorpay | cash
    method = models.CharField(max_length=20, blank=True)
    razorpay_order_id = models.CharField(max_length=40, blank=True, db_index=True)
    razorpay_payment_id = models.CharField(max_length=40, blank=True, db_index=True)
    account_key_id = models.CharField(max_length=64, blank=True, help_text="Razorpay account the money went to")
    account_source = models.CharField(max_length=16, blank=True)
    settlement_status = models.CharField(max_length=10, default="pending")  # pending | settled | mismatch
    customer_name = models.CharField(max_length=150, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class Refund(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="refunds")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, default="pending")  # pending | processed | failed
    gateway_refund_id = models.CharField(max_length=40, blank=True)
    created_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Receipt(models.Model):
    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="receipt")
    invoice_number = models.CharField(max_length=30)
    generated_at = models.DateTimeField(auto_now_add=True)
    printed = models.BooleanField(default=False)
    download_count = models.PositiveIntegerField(default=0)
    email_status = models.CharField(max_length=20, default="not sent")
    emailed_to = models.EmailField(blank=True)
    whatsapp_status = models.CharField(max_length=20, default="not sent")


class PaymentAudit(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, null=True, blank=True, related_name="audit")
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, null=True, blank=True, related_name="payment_audit")
    action = models.CharField(max_length=40)
    description = models.CharField(max_length=255, blank=True)
    user = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
