from django.contrib import admin
from django.utils.html import format_html

from .models import (
    RestaurantGatewaySettings,
    PaymentTransaction,
    PaymentRefund,
    PaymentWebhookLog,
    PaymentAuditLog,
    Receipt,
)


# ==========================================================
# Receipt Inline
# ==========================================================

class ReceiptInline(admin.StackedInline):
    model = Receipt
    extra = 0
    can_delete = False
    readonly_fields = (
        "receipt_number",
        "pdf",
        "created_at",
        "printed",
        "printed_at",
        "email_sent",
        "email_sent_at",
        "whatsapp_sent",
        "whatsapp_sent_at",
    )


# ==========================================================
# Refund Inline
# ==========================================================

class PaymentRefundInline(admin.TabularInline):
    model = PaymentRefund
    extra = 0
    readonly_fields = (
        "refund_id",
        "amount",
        "status",
        "reason",
        "created_at",
    )


# ==========================================================
# Gateway Settings
# ==========================================================

@admin.register(RestaurantGatewaySettings)
class RestaurantGatewaySettingsAdmin(admin.ModelAdmin):

    list_display = (
        "restaurant",
        "gateway",
        "environment",
        "verified",
        "accept_online",
        "accept_cash_delivery",
        "accept_cash_pickup",
        "is_active",
    )

    list_filter = (
        "gateway",
        "environment",
        "verified",
        "accept_online",
        "accept_cash_delivery",
        "accept_cash_pickup",
        "is_active",
    )

    search_fields = (
        "restaurant__name",
        "merchant_name",
        "merchant_email",
    )

    readonly_fields = (
        "merchant_name",
        "merchant_email",
        "verified",
        "verified_at",
        "last_verified_at",
        "last_payment_received_at",
        "created_at",
        "updated_at",
        "masked_key_id",
        "masked_secret",
        "masked_webhook",
    )

    exclude = (
        "encrypted_razorpay_key_id",
        "encrypted_razorpay_key_secret",
        "encrypted_webhook_secret",
    )

    fieldsets = (

        ("Restaurant", {
            "fields": (
                "restaurant",
                "gateway",
                "environment",
                "currency",
            )
        }),

        ("Credentials", {
            "fields": (
                "masked_key_id",
                "masked_secret",
                "masked_webhook",
            )
        }),

        ("Payment Options", {
            "fields": (
                "accept_online",
                "accept_cash_delivery",
                "accept_cash_pickup",
                "is_active",
            )
        }),

        ("Verification", {
            "fields": (
                "verified",
                "verified_at",
                "last_verified_at",
                "last_payment_received_at",
            )
        }),

        ("Timestamps", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),

    )

    def mask(self, value):

        if not value:
            return "-"

        if len(value) < 8:
            return "********"

        return "********" + value[-4:]

    def masked_key_id(self, obj):
        return self.mask(obj.razorpay_key_id)

    masked_key_id.short_description = "Razorpay Key ID"

    def masked_secret(self, obj):
        return self.mask(obj.razorpay_secret)

    masked_secret.short_description = "Key Secret"

    def masked_webhook(self, obj):
        return self.mask(obj.webhook_secret_value)

    masked_webhook.short_description = "Webhook Secret"


# ==========================================================
# Payment Transaction
# ==========================================================

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):

    inlines = [
        PaymentRefundInline,
        ReceiptInline,
    ]

    list_display = (
        "transaction_number",
        "restaurant",
        "customer_name",
        "payment_mode",
        "source",
        "amount",
        "status",
        "otp_verified",
        "paid_at",
    )

    list_filter = (
        "status",
        "payment_mode",
        "source",
        "otp_verified",
        "is_deleted",
        "created_at",
    )

    search_fields = (
        "transaction_number",
        "gateway_order_id",
        "gateway_payment_id",
        "customer_name",
        "customer_phone",
        "restaurant__name",
    )

    readonly_fields = (
        "id",
        "transaction_number",
        "gateway_order_id",
        "gateway_payment_id",
        "gateway_signature",
        "gateway_response",
        "created_at",
        "updated_at",
        "paid_at",
        "otp_verified",
        "otp_verified_at",
    )

    date_hierarchy = "created_at"

    ordering = ("-created_at",)


# ==========================================================
# Refunds
# ==========================================================

@admin.register(PaymentRefund)
class PaymentRefundAdmin(admin.ModelAdmin):

    list_display = (
        "payment",
        "refund_id",
        "amount",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "refund_id",
        "payment__transaction_number",
    )

    readonly_fields = (
        "gateway_response",
        "created_at",
    )


# ==========================================================
# Webhook Logs
# ==========================================================

@admin.register(PaymentWebhookLog)
class PaymentWebhookLogAdmin(admin.ModelAdmin):

    list_display = (
        "restaurant",
        "event",
        "verified",
        "processed",
        "received_at",
    )

    list_filter = (
        "verified",
        "processed",
        "received_at",
    )

    search_fields = (
        "restaurant__name",
        "event",
    )

    readonly_fields = (
        "payload",
        "headers",
        "signature",
        "error_message",
        "processed_at",
        "received_at",
    )


# ==========================================================
# Audit Logs
# ==========================================================

@admin.register(PaymentAuditLog)
class PaymentAuditLogAdmin(admin.ModelAdmin):

    list_display = (
        "action",
        "restaurant",
        "payment",
        "user",
        "created_at",
    )

    list_filter = (
        "action",
        "created_at",
    )

    search_fields = (
        "restaurant__name",
        "description",
        "payment__transaction_number",
    )

    readonly_fields = (
        "created_at",
    )


# ==========================================================
# Receipts
# ==========================================================

@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):

    list_display = (
        "receipt_number",
        "payment",
        "printed",
        "email_sent",
        "whatsapp_sent",
        "created_at",
    )

    list_filter = (
        "printed",
        "email_sent",
        "whatsapp_sent",
    )

    search_fields = (
        "receipt_number",
        "payment__transaction_number",
    )

    readonly_fields = (
        "created_at",
        "printed_at",
        "email_sent_at",
        "whatsapp_sent_at",
    )