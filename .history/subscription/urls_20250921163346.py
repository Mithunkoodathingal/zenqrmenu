# subscription/url

from django.urls import path
from .views import *

urlpatterns = [
    path('', subscription_plans, name='subscription_plans'),  # View available plans
    path('create/<int:plan_id>/', create_subscription, name='create_subscription'),  # Subscribe & pay
    path('payment-success/', payment_success, name='payment_success'),  # Handle successful payment
    path('<int:pk>/', SubscriptionDetailView.as_view(), name='subscription_detail'),  # Subscription details
    path('<int:pk>/cancel/', SubscriptionCancelView.as_view(), name='subscription_cancel'),  # Cancel subscription
]
