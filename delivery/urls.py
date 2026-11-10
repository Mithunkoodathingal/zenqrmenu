from django.urls import path

from . import views

urlpatterns = [
    path("api/delivery-partners/", views.PartnerList.as_view()),
    path("api/delivery-partners/<int:pk>/", views.PartnerDetail.as_view()),
    path("api/delivery-partners/<int:pk>/availability/", views.availability),
    path("api/delivery-partners/<int:pk>/location/", views.owner_location),
    path("api/orders/<int:pk>/assign-partner/", views.assign),
    path("api/orders/<int:pk>/unassign-partner/", views.unassign),
    path("api/delivery/my-assignments/", views.my_assignments),
    path("api/delivery/availability/", views.my_availability),
    path("api/delivery/assignments/<int:pk>/start/", views.start_trip),
    path("api/delivery/assignments/<int:pk>/delivered/", views.delivered),
    path("api/delivery/assignments/<int:pk>/location/", views.trip_location),
]
