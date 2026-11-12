from django.urls import path

from . import auth_views, views

urlpatterns = [
    path("api/customers/auth/register/", auth_views.register),
    path("api/customers/auth/verify-email/", auth_views.verify_email),
    path("api/customers/auth/resend-code/", auth_views.resend_code),
    path("api/customers/auth/login/", auth_views.login),
    path("api/customers/auth/password/forgot/", auth_views.forgot_password),
    path("api/customers/auth/password/reset/", auth_views.reset_password),
    path("api/customers/me/password/", auth_views.change_password),
    path("api/customers/auth/refresh/", views.refresh),
    path("api/customers/me/", views.MeView.as_view()),
    path("api/customers/me/addresses/", views.AddressList.as_view()),
    path("api/customers/me/addresses/<int:pk>/", views.AddressDetail.as_view()),
    path("api/customers/me/addresses/<int:pk>/set-default/", views.set_default),
    path("api/customers/me/orders/", views.my_orders),
    path("api/customers/me/orders/<int:pk>/", views.my_order),
]
