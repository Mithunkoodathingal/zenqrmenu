from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from payments.utils import encrypt, decrypt
from restaurant.models import Restaurant, Order
import uuid
import random
import string
from restaurant.models import Order
from .models import (
    RestaurantGatewaySettings,
    PaymentTransaction,
    PaymentAuditLog,
)




# ==========================================
# Restaurant Payment Settings
# ==========================================

class RestaurantGatewaySettings(models.Model):

    GATEWAY_CHOICES = [
        ("razorpay", "Razorpay"),
        ("stripe", "Stripe"),
        ("cashfree", "Cashfree"),
    ]

    ENVIRONMENT_CHOICES = [
        ("test", "Test"),
        ("live", "Live"),
    ]

    restaurant = models.OneToOneField(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="payment_settings"
    )

    gateway = models.CharField(
        max_length=30,
        choices=GATEWAY_CHOICES,
        default="razorpay"
    )

    environment = models.CharField(
        max_length=10,
        choices=ENVIRONMENT_CHOICES,
        default="live"
    )

    currency = models.CharField(
        max_length=5,
        default="INR"
    )

    encrypted_razorpay_key_id = models.TextField(blank=True)

    @property
    def razorpay_key_id(self):
        return decrypt(self.encrypted_razorpay_key_id)


    @razorpay_key_id.setter
    def razorpay_key_id(self, value):
        self.encrypted_razorpay_key_id = encrypt(value)

    encrypted_razorpay_key_secret = models.TextField(
        blank=True
    )

    encrypted_webhook_secret = models.TextField(
        blank=True
    )

    merchant_name = models.CharField(
        max_length=255,
        blank=True,
        editable=False
    )

    merchant_email = models.EmailField(
        blank=True,
        editable=False
    )

    verified = models.BooleanField(default=False)

    verified_at = models.DateTimeField(
        null=True,
        blank=True
    )

    last_verified_at = models.DateTimeField(
        null=True,
        blank=True
    )

    last_payment_received_at = models.DateTimeField(
        null=True,
        blank=True
    )

    accept_online = models.BooleanField(default=False)

    accept_cash_delivery = models.BooleanField(default=False)

    accept_cash_pickup = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    @property
    def razorpay_key_secret(self):
        return decrypt(
            self.encrypted_razorpay_key_secret
        )

    @razorpay_key_secret.setter
    def razorpay_key_secret(self, value):

        self.encrypted_razorpay_key_secret = encrypt(value)

    @property
    def webhook_secret(self):
        return decrypt(
            self.encrypted_webhook_secret
        )

    @webhook_secret.setter
    def webhook_secret(self, value):
        self.encrypted_webhook_secret = encrypt(value)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Payment Gateway"
        verbose_name_plural = "Payment Gateways"

    def __str__(self):
        return f"{self.restaurant.name} Payment Settings"
    

class PaymentTransaction(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Human-readable transaction number
    transaction_number = models.CharField(
        max_length=25,
        unique=True,
        blank=True,
    )

    # Soft delete
    is_deleted = models.BooleanField(
        default=False
    )

    PAYMENT_MODE = [
        ("online", "Online"),
        ("cash", "Cash"),
    ]
    SOURCE_CHOICES = [
        ("dinein","Dine In"),
        ("pickup","Pickup"),
        ("delivery","Delivery"),
        ("website","Website"),
    ]

    STATUS = [

    ("created","Created"),

    ("pending","Pending"),

    ("authorized","Authorized"),

    ("captured","Captured"),

    ("paid","Paid"),

    ("failed","Failed"),

    ("cancelled","Cancelled"),

    ("expired","Expired"),

    ("refunded","Refunded"),

    ("partially_refunded","Partially Refunded")

    ]

    completion_otp = models.CharField(
        max_length=6,
        blank=True,
        db_index=True,
    )

    otp_verified = models.BooleanField(
        default=False
    )

    otp_verified_at = models.DateTimeField(
        null=True,
        blank=True
    )

    otp_expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default="dinein"
    )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="payment"
    )

    customer_country = models.CharField(
        max_length=100,
        default="India"
    )

    customer_country_code = models.CharField(
        max_length=6,
        default="+91"
    )

    gateway = models.CharField(
        max_length=30,
        default="razorpay"
    )

    payment_mode = models.CharField(
        max_length=30,
        choices=PAYMENT_MODE
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="created",
        db_index=True,
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    gateway_fee_percentage  = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    gateway_tax_percentage  = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    net_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    currency = models.CharField(
        max_length=5,
        default="INR"
    )

    gateway_order_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
    )

    gateway_payment_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
    )

    gateway_signature = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )
    gateway_response = models.JSONField(
        default=dict,
        blank=True
    )
    failure_reason = models.TextField(
        blank=True,
        null=True
    )
    delivery_person_name = models.CharField(
        max_length=100,
        blank=True
    )

    delivery_person_phone = models.CharField(
        max_length=20,
        blank=True
    )

    delivery_started_at = models.DateTimeField(
        null=True,
        blank=True
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_payments"
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True
    )

    remarks = models.TextField(
        blank=True
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["payment_mode"]),
            models.Index(fields=["restaurant"]),
            models.Index(fields=["created_at"]),
        ]
        verbose_name = "Payment Transaction"
        verbose_name_plural = "Payment Transactions"


    @property
    def whatsapp_number(self):
        return (
            self.customer_country_code.replace("+", "")
            + self.order.customer_phone
        )


    def save(self, *args, **kwargs):

        if not self.transaction_number:

            while True:

                random_part = ''.join(
                    random.choices(
                        string.ascii_uppercase + string.digits,
                        k=6
                    )
                )

                number = f"TXN-{timezone.now().strftime('%Y%m%d')}-{random_part}"

                if not PaymentTransaction.objects.filter(
                    transaction_number=number
                ).exists():

                    self.transaction_number = number
                    break

        super().save(*args, **kwargs)

    def soft_delete(self):

        self.is_deleted = True
        self.save(update_fields=["is_deleted"])

    def __str__(self):
        return f"{self.restaurant.name} - ₹{self.amount}"
    

class PaymentRefund(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    STATUS = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("processed", "Processed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    payment = models.ForeignKey(
        PaymentTransaction,
        on_delete=models.CASCADE,
        related_name="refunds"
    )

    refund_id = models.CharField(
        max_length=255,
        blank=True
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    reason = models.TextField()

    gateway_response = models.JSONField(
        default=dict,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="pending",
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Payment Refund"
        verbose_name_plural = "Payment Refunds"

    def __str__(self):
        return f"{self.payment} - {self.status}"


class PaymentWebhookLog(models.Model):

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE
    )

    event = models.CharField(
        max_length=200
    )

    payload = models.JSONField()

    signature = models.CharField(
        max_length=255,
        blank=True
    )

    headers = models.JSONField(
        default=dict
    )

    verified = models.BooleanField(
        default=False
    )

    received_at = models.DateTimeField(
        auto_now_add=True
    )

    error_message = models.TextField(
        blank=True
    )

    processed = models.BooleanField(
        default=False
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-received_at"]

        verbose_name = "Payment Webhook"

        verbose_name_plural = "Payment Webhooks"

    def __str__(self):
        return f"{self.restaurant.name} - {self.event}"


class PaymentAuditLog(models.Model):

    ACTIONS = [
        ("created", "Created"),
        ("verified", "Verified"),
        ("updated", "Updated"),
        ("payment", "Payment"),
        ("refund", "Refund"),
        ("failed", "Failed"),
        ("reconciliation", "Reconciliation"),
    ]

    user = models.ForeignKey(

        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE
    )

    payment = models.ForeignKey(
        PaymentTransaction,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    action = models.CharField(
        max_length=30,
        choices=ACTIONS
    )

    description = models.TextField()

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Payment Audit Log"
        verbose_name_plural = "Payment Audit Logs"

    def __str__(self):
        return f"{self.action} - {self.restaurant.name}"


class Receipt(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="receipts",
        editable=False,
    )

    payment = models.OneToOneField(
        PaymentTransaction,
        on_delete=models.CASCADE,
        related_name="receipt"
    )

    pdf = models.FileField(
        upload_to="receipts/",
        blank=True,
        null=True
    )

    invoice_number = models.CharField(
        max_length=30,
        blank=True
    )

    invoice_date = models.DateTimeField(
        default=timezone.now
    )


    # =========================
    # Receipt Delivery Status
    # =========================

    whatsapp_sent = models.BooleanField(
        default=False
    )

    whatsapp_sent_at = models.DateTimeField(
        null=True,
        blank=True
    )

    email_sent = models.BooleanField(
        default=False
    )

    email_sent_at = models.DateTimeField(
        null=True,
        blank=True
    )

    printed = models.BooleanField(
        default=False
    )

    printed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    pdf_generated_at = models.DateTimeField(
        null=True,
        blank=True
    )

    download_count = models.PositiveIntegerField(
        default=0
    )

    last_downloaded_at = models.DateTimeField(
        null=True,
        blank=True
    )

    emailed_to = models.EmailField(
        blank=True
    )

    whatsapp_number = models.CharField(
        max_length=20,
        blank=True
    )

    notes = models.TextField(
        blank=True
    )

    class Meta:
        indexes = [

            models.Index(
                fields=["restaurant"]
            ),

            models.Index(
                fields=["invoice_number"]
            ),

            models.Index(
                fields=[
                    "restaurant",
                    "invoice_number",
                ]
            ),

        ]
        ordering = ["-created_at"]
        verbose_name = "Receipt"
        verbose_name_plural = "Receipts"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "restaurant",
                    "invoice_number",
                ],
                name="unique_restaurant_invoice_number",
            ),
        ]

    def save(self, *args, **kwargs):

        if not self.restaurant_id:

            self.restaurant = self.payment.restaurant

        super().save(*args, **kwargs)


    def __str__(self):
        return f"Receipt {self.invoice_number}"


