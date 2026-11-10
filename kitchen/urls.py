from django.urls import path

from . import views

urlpatterns = [
    path("kds/orders/", views.kds_orders),
    path("kds/orders/<int:pk>/status/", views.kds_status),
    path("kds/orders/<int:pk>/priority/", views.kds_priority),
    path("kds/orders/<int:pk>/notes/", views.kds_note),
    path("kds/statistics/", views.statistics),
    path("kitchen/notes/", views.notes),
    path("kitchen/notes/<int:pk>/", views.note_detail),
]
