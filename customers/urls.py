from django.urls import path

from . import views

urlpatterns = [
    path("api/customers/auth/email/request-otp/", views.request_code),
    path("api/customers/auth/email/verify-otp/", views.verify_code),
    path("api/customers/auth/refresh/", views.refresh),
    path("api/customers/me/", views.MeView.as_view()),
    path("api/customers/me/addresses/", views.AddressList.as_view()),
    path("api/customers/me/addresses/<int:pk>/", views.AddressDetail.as_view()),
    path("api/customers/me/addresses/<int:pk>/set-default/", views.set_default),
    path("api/customers/me/orders/", views.my_orders),
    path("api/customers/me/orders/<int:pk>/", views.my_order),
]
