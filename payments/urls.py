from django.urls import path

from . import views

urlpatterns = [
    path("payments/api/payment-settings/", views.SettingsView.as_view()),
    path("payments/api/payment-settings/verify/", views.verify_settings),
    path("api/payment-settings/incentive/", views.IncentiveView.as_view()),
    path("api/branches/payment-accounts/", views.branch_accounts),
    path("api/branches/<int:pk>/payment-account/", views.branch_account),
    path("api/branches/<int:pk>/payment-account/verify/", views.verify_branch_account),
    path("payments/orders/<int:pk>/create-payment/", views.create_payment),
    path("payments/orders/<int:pk>/verify-payment/", views.verify_payment),
    path("payments/webhook/razorpay/", views.webhook),
    path("payments/payments/history/", views.history),
    path("payments/payments/<int:pk>/", views.payment_detail),
    path("payments/orders/<int:pk>/refund/", views.create_refund),
    path("payments/orders/<int:pk>/refund-status/", views.refund_status),
    path("payments/receipt/<int:order_id>/", views.receipt),
    path("payments/orders/<int:order_id>/receipt/pdf/", views.receipt_pdf),
    path("payments/orders/<int:order_id>/receipt/email/", views.receipt_email),
    path("payments/orders/<int:order_id>/receipt/whatsapp/", views.receipt_whatsapp),
    path("api/payments/reconciliation/", views.reconciliation),
    path("api/payments/reconciliation/run/", views.run_reconciliation),
    path("api/payments/reconciliation/<int:order_id>/resolve/", views.resolve_reconciliation),
]
