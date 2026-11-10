from django.urls import path

from . import views

urlpatterns = [
    path("api/coupons/", views.CouponList.as_view()),
    path("api/coupons/<int:pk>/", views.CouponDetail.as_view()),
    path("api/restaurants/<int:pk>/coupons/validate/", views.validate),
    path("api/public/restaurants/<int:pk>/offers/", views.offers),
]
