from django.urls import path

from . import views

urlpatterns = [
    path("menu/api/orders/", views.OrderList.as_view()),
    path("menu/api/orders/<int:pk>/", views.OrderDetail.as_view()),
    path("menu/api/orders/<int:pk>/public/", views.public_order),
    path("menu/api/table/<int:pk>/orders/", views.table_orders),
    path("payments/orders/<int:pk>/generate-otp/", views.generate_code),
    path("payments/orders/<int:pk>/verify-otp/", views.verify_code),
    path("payments/orders/<int:pk>/complete/", views.complete),
]
