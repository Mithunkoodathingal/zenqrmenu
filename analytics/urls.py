from django.urls import path

from . import views

A = "menu/api/analytics/"
urlpatterns = [
    path("menu/api/dashboard/widgets/", views.widgets),
    path(A + "executive/", views.executive),
    path(A + "summary/", views.summary),
    path(A + "sales/", views.sales),
    path(A + "daily-sales/", views.daily_sales),
    path(A + "monthly-sales/", views.monthly_sales),
    path(A + "heatmap/", views.heatmap),
    path(A + "revenue/", views.revenue),
    path(A + "payment-methods/", views.payment_methods),
    path(A + "refunds/", views.refunds),
    path(A + "menu/", views.menu),
    path(A + "top-customers/", views.top_customers),
    path(A + "top-items/", views.top_items),
    path(A + "customers/", views.customers),
    path(A + "delivery/", views.delivery),
    path(A + "kitchen/", views.kitchen),
    path(A + "coupons/", views.coupons),
    path(A + "staff/", views.staff),
    path("menu/api/reports/export/", views.export),
    path("menu/api/reports/scheduled/", views.scheduled),
    path("menu/api/reports/scheduled/<int:pk>/", views.scheduled_detail),
]
