from django.urls import path

from . import views

urlpatterns = [
    path("api/marketing/customers/", views.Customers.as_view()),
    path("api/marketing/campaigns/", views.CampaignList.as_view()),
    path("api/marketing/campaigns/preview/", views.preview),
    path("api/marketing/campaigns/<int:pk>/", views.CampaignDetail.as_view()),
    path("api/marketing/campaigns/<int:pk>/send/", views.send),
    path("api/marketing/unsubscribe-link/<str:email>/", views.unsubscribe_link),
    path("api/marketing/unsubscribe/<str:token>/", views.unsubscribe),
    path("api/marketing/consent/", views.consent),
]
