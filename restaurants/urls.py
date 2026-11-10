from django.urls import path

from . import views

urlpatterns = [
    path("menu/api/restaurant/", views.ProfileView.as_view()),
    path("menu/api/restaurant/location/", views.LocationView.as_view()),
    path("menu/api/restaurant/delivery-zone/", views.ZoneView.as_view()),
    path("menu/api/restaurant/working-hours/", views.HoursView.as_view()),
    path("menu/api/restaurant/settings/", views.SettingsView.as_view()),
    path("api/branches/", views.BranchList.as_view()),
    path("api/branches/<int:pk>/", views.BranchDetail.as_view()),
    path("menu/api/tables/", views.TableList.as_view()),
    path("menu/api/tables/<int:pk>/", views.TableDetail.as_view()),
    path("menu/api/qr/table/<int:pk>/", views.qr_table),
    path("menu/api/qr/pickup/", views.qr_pickup),
    path("menu/api/qr/delivery/", views.qr_delivery),
    path("api/public/restaurants/nearby/", views.nearby),
    path("menu/api/restaurants/nearby/", views.nearby),
    path("api/public/restaurants/<int:pk>/", views.public_restaurant),
    path("menu/api/delivery/quote/", views.quote),
]
