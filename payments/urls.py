from django.urls import path
from .views.payment_settings import *
from .views.otp import *
from .views.audit import *
from .views.history import *
from .views.order_completion import *
from .views.payment_orders import *
from .views.receipt import *
from .views.reconciliation import *
from .views.refunds import *
from .views.webhooks import *

urlpatterns = [

    path(
        "api/payment-settings/",
        PaymentSettingsAPIView.as_view(),
    ),

    path(
        "api/payment-settings/verify/",
        VerifyRazorpayAPIView.as_view(),
    ),

    path(
        "orders/<uuid:order_id>/verify-payment/",
        VerifyPaymentAPIView.as_view(),
        name="verify-payment",
    ),

    path(
        "orders/<uuid:order_id>/generate-otp/",
        GenerateOTPAPIView.as_view(),
        name="generate-otp",
    ),
    path(
        "orders/<uuid:order_id>/verify-otp/",
        VerifyOTPAPIView.as_view(),
        name="verify-otp",
    ),

    path(
        "orders/<uuid:order_id>/complete/",
        CompleteOrderAPIView.as_view(),
        name="complete-order",
    ),

    path(
        "webhook/razorpay/",
        RazorpayWebhookAPIView.as_view(),
        name="razorpay-webhook",
    ),

    path(
        "orders/<uuid:order_id>/create-payment/",
        CreateRazorpayOrderAPIView.as_view(),
        name="create-payment",
    ),

    path(
        "receipt/<uuid:order_id>/",
        ReceiptAPIView.as_view(),
        name="receipt",
    ),

    path(
        "orders/<uuid:order_id>/refund/",
        RefundAPIView.as_view(),
        name="refund",
    ),

    path(
        "orders/<uuid:order_id>/refund-status/",
        RefundStatusAPIView.as_view(),
        name="refund-status",
    ),
    path(
        "payments/history/",
        PaymentHistoryAPIView.as_view(),
        name="payment-history",
    ),

    path(
        "payments/<uuid:payment_id>/",
        PaymentDetailAPIView.as_view(),
        name="payment-detail",
    ),
    path(
        "orders/<uuid:order_id>/receipt/pdf/",
        ReceiptPDFAPIView.as_view(),
        name="receipt-pdf",
    ),
    path(
        "orders/<uuid:order_id>/receipt/email/",
        EmailReceiptAPIView.as_view(),
        name="receipt-email",
    ),
    path(
        "orders/<uuid:order_id>/receipt/whatsapp/",
        WhatsAppReceiptAPIView.as_view(),
        name="receipt-whatsapp",
    ),
]