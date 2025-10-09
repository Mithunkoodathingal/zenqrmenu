subscription/views.py
import razorpay
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import SubscriptionPlan, Subscription
from django.shortcuts import render, redirect
from django.views.generic import CreateView, DetailView, View
from django.urls import reverse_lazy
from restaurant.models import Restaurant
from django.http import JsonResponse
from django.utils.timezone import now
from decimal import Decimal
import requests
from requests.auth import HTTPBasicAuth

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@login_required
def subscription_plans(request):
    """Show available subscription plans with table limits."""
    plans = [
        {"name": "Basic Plan", "price": 50, "duration_days": 30, "table_limit": 10},
        {"name": "Standard Plan", "price": 100, "duration_days": 30, "table_limit": 20},
        {"name": "Premium Plan", "price": 150, "duration_days": 30, "table_limit": 35},
    ]

    for plan_data in plans:
        plan, created = SubscriptionPlan.objects.get_or_create(price=plan_data["price"], defaults=plan_data)

    plans = SubscriptionPlan.objects.all()
    return render(request, 'subscription/subscription_plans.html', {'plans': plans})


@login_required
def create_subscription(request, plan_id):
    """Create a payment order for a subscription"""
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    restaurant = request.user.restaurant

    # Convert Decimal price to int (paisa)
    order_amount = int(plan.price * Decimal(100))  # Convert ₹1 to 100 paisa
    order_currency = 'INR'

    # Create Razorpay order
    order_data = {
        "amount": order_amount,
        "currency": order_currency,
        "payment_capture": 1,  # Auto-capture payment
    }
    order = razorpay_client.order.create(data=order_data)

    # Store order details in session for later verification
    request.session['order_id'] = order['id']
    request.session['plan_id'] = plan.id

    response = requests.get(
            "https://api.razorpay.com/v1/methods",
            auth=HTTPBasicAuth(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

    print(response.json())

    return render(request, 'subscription/payment.html', {
        'plan': plan,
        'order_id': order['id'],
        'amount': order_amount / 100,  # Convert paisa back to ₹
        'razorpay_key': settings.RAZORPAY_KEY_ID,
    })




@login_required
def payment_success(request):
    """Verify payment and activate subscription"""
    order_id = request.session.get('order_id')
    plan_id = request.session.get('plan_id')

    if not order_id or not plan_id:
        messages.error(request, "Invalid payment session.")
        return redirect('subscription_plans')

    # Fetch the subscription plan
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    restaurant = request.user.restaurant

    # Activate or create a subscription for the restaurant
    subscription, created = Subscription.objects.get_or_create(restaurant=restaurant)
    subscription.plan = plan
    subscription.activate()  # Set start_date and end_date
    subscription.is_active = True
    subscription.save()

    # Clear session data after successful payment
    del request.session['order_id']
    del request.session['plan_id']

    messages.success(request, f"Subscription activated! Valid until {subscription.end_date.date()}")
    return redirect('dashboard')


class SubscriptionCreateView(CreateView):
    model = Subscription
    fields = ['plan', 'payment_status']
    template_name = 'subscription/subscribe.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        form.instance.restaurant = self.request.user.restaurant
        return super().form_valid(form)

# Subscription Detail View
class SubscriptionDetailView(DetailView):
    model = Subscription
    template_name = 'subscription/subscription_detail.html'

# Cancel Subscription
class SubscriptionCancelView(View):
    def post(self, request, pk):
        subscription = Subscription.objects.get(pk=pk)
        subscription.is_active = False  # Mark subscription as inactive
        subscription.save()
        return redirect('dashboard')
