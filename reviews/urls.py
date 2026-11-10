from django.urls import path

from . import views

urlpatterns = [
    path("api/restaurants/<int:pk>/reviews/", views.restaurant_reviews),
    path("api/reviews/", views.owner_reviews),
    path("api/reviews/<int:pk>/", views.owner_review),
    path("api/customers/me/orders/<int:pk>/review-eligibility/", views.review_eligibility),
    path("api/customers/me/orders/<int:pk>/review/", views.write_review),
    path("api/customers/me/reviews/", views.my_reviews),
    path("api/customers/me/reviews/<int:pk>/", views.my_review),
]
