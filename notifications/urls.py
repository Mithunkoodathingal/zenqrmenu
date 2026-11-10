from django.urls import path

from . import views

urlpatterns = [
    path("menu/api/notifications/", views.notifications),
    path("menu/api/notifications/read-all/", views.read_all),
    path("menu/api/notifications/preferences/", views.preferences),
    path("menu/api/notifications/test/", views.test),
    path("menu/api/notifications/<int:pk>/read/", views.read_one),
]
