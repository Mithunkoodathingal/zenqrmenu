from django.urls import path

from . import views

urlpatterns = [
    path("subscription/api/plans/", views.plans),
    path("subscription/api/subscription/", views.status_view),
    path("subscription/api/current/", views.current),
    path("subscription/api/usage/", views.usage),
    path("subscription/api/invoices/", views.invoices),
    path("subscription/api/create/", views.create),
    path("subscription/api/upgrade/", views.upgrade),
    path("subscription/api/verify/", views.verify),
    path("subscription/api/cancel/", views.cancel),
]
