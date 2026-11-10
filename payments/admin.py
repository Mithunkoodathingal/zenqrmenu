from django.contrib import admin

from .models import BranchPaymentAccount, Payment, PaymentIncentive, PaymentSettings, Receipt, Refund


@admin.register(PaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ("restaurant", "razorpay_key_id", "environment", "accept_online", "verified")
    exclude = ("key_secret_enc", "webhook_secret_enc")


@admin.register(BranchPaymentAccount)
class BranchPaymentAccountAdmin(admin.ModelAdmin):
    list_display = ("branch", "mode", "razorpay_key_id", "verified")
    exclude = ("key_secret_enc",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "restaurant", "order", "amount", "status", "gateway", "settlement_status", "created_at")
    list_filter = ("status", "gateway", "settlement_status")
    search_fields = ("transaction_id", "razorpay_payment_id", "razorpay_order_id", "order__order_number")


admin.site.register(PaymentIncentive)
admin.site.register(Refund)
admin.site.register(Receipt)
