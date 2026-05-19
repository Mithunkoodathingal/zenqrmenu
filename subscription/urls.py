# subscription/urls.py

from django.urls import path
from .views import *

app_name = "subscription"   # <-- important for namespacing

urlpatterns = [
    path('', subscription_plans, name='subscription_plans'),  # View available plans

    ######### API URL'S #########
    path('api/plans/', subscription_plans_api, name='subscription_plans_api'),
    path('api/create/', api_create_subscription),
    path('api/verify/', api_verify_payment),
    path('api/subscription/', subscription_status),
    path('menu/api/subscription/', subscription_status),

    # path('create/<int:plan_id>/', create_subscription, name='create_subscription'),  # Subscribe & pay
    path('webhook/', payment_success_webhook, name='payment_webhook'),
    path('payment-success/', payment_success_return, name='payment_success'),  # Handle successful payment
    path('<int:pk>/', SubscriptionDetailView.as_view(), name='subscription_detail'),  # Subscription details
    path('<int:pk>/cancel/', SubscriptionCancelView.as_view(), name='subscription_cancel'),  # Cancel subscription
    
]
