# subscription/views.py
import razorpay
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import SubscriptionPlan, Subscription
from django.views.generic import CreateView, DetailView, View
from django.urls import reverse_lazy
from restaurant.models import Restaurant
from decimal import Decimal
from django.views.decorators.http import require_POST

# initialize client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@login_required
def subscription_plans(request):
    """
    Ensure four default plans exist (editable in admin) and render plans page.
    Uses get_or_create by name to avoid MultipleObjectsReturned when admins
    create rows with same price.
    """
    # default_plans = [
    #     {"name": "Free", "price": Decimal("0.00"), "duration_days": 30, "table_limit": 1,
    #      "features": "Unlimited scans, unlimited categories & items"},
    #     {"name": "Small (₹100)", "price": Decimal("100.00"), "duration_days": 30, "table_limit": 10,
    #      "features": "Unlimited scans, unlimited categories & items"},
    #     {"name": "Medium (₹200)", "price": Decimal("200.00"), "duration_days": 30, "table_limit": 20,
    #      "features": "Unlimited scans, unlimited categories & items"},
    #     {"name": "Pro (₹500)", "price": Decimal("500.00"), "duration_days": 30, "table_limit": 100,
    #      "features": "Ideal for hotels, unlimited scans, categories & items"},
    # ]

    # Create missing default plans by name (safe against duplicates by price)
    for p in default_plans:
        # use name as the unique key for seeding defaults
        SubscriptionPlan.objects.get_or_create(name=p["name"], defaults={
            "price": p["price"],
            "duration_days": p["duration_days"],
            "table_limit": p["table_limit"],
            "features": p["features"],
        })

    # Fetch plans to show on page — order by price for user-friendly display
    plans = SubscriptionPlan.objects.all().order_by('price', 'id')
    return render(request, 'subscription/subscription_plans.html', {'plans': plans})

@login_required
def create_subscription(request, plan_id):
    """
    Create a subscription order. For free plans (price == 0) bypass payment and activate immediately.
    Only the restaurant owner may create a subscription for their restaurant.
    """
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)

    # Ensure restaurant ownership
    restaurant = get_object_or_404(Restaurant, owner=request.user)

    # If free plan -> directly create/replace subscription and activate
    if plan.price == Decimal("0.00"):
        subscription, created = Subscription.objects.get_or_create(restaurant=restaurant)
        subscription.plan = plan
        subscription.activate()
        messages.success(request, f"Free plan activated. Valid until {subscription.end_date.date()}")
        return redirect('dashboard')

    # For paid plans -> create Razorpay order
    order_amount_paisa = int(plan.price * Decimal(100))  # paisa (int)
    order_currency = 'INR'
    order_data = {
        "amount": order_amount_paisa,
        "currency": order_currency,
        "payment_capture": 1,
    }
    order = razorpay_client.order.create(data=order_data)

    # store minimal verification context in session
    request.session['subscription_order'] = {
        'order_id': order['id'],
        'plan_id': plan.id,
        'restaurant_id': restaurant.id,
    }

    # allow user to opt-in auto_renew on frontend (persisting auto_renew needs a model change)
    # We'll read POST param if sent (or default False)
    auto_renew = bool(request.POST.get('auto_renew', False))
    request.session['subscription_order']['auto_renew'] = auto_renew

    # Render payment page. We pass amount in paisa (fixes previous mismatch)
    return render(request, 'subscription/payment.html', {
        'plan': plan,
        'order_id': order['id'],
        'amount_paisa': order_amount_paisa,
        'razorpay_key': settings.RAZORPAY_KEY_ID,
    })


@require_POST
@login_required
def payment_success(request):
    """
    Razorpay posts back (callback_url) with razorpay_payment_id, razorpay_order_id, razorpay_signature.
    We verify the signature server-side and then activate/replace subscription.
    """
    payload = request.POST
    razorpay_payment_id = payload.get('razorpay_payment_id')
    razorpay_order_id = payload.get('razorpay_order_id')
    razorpay_signature = payload.get('razorpay_signature')

    session_info = request.session.get('subscription_order')
    if not session_info:
        messages.error(request, "Missing payment session. Try again.")
        return redirect('subscription_plans')

    expected_order_id = session_info.get('order_id')
    plan_id = session_info.get('plan_id')
    restaurant_id = session_info.get('restaurant_id')

    # Basic checks
    if expected_order_id != razorpay_order_id:
        messages.error(request, "Order mismatch. Payment not verified.")
        return redirect('subscription_plans')

    try:
        # Server-side signature verification (raises exception on mismatch)
        razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        })
    except Exception as e:
        # Log and return error (don't activate subscription)
        messages.error(request, "Payment verification failed. Contact support.")
        # optional: logger.exception(e)
        return redirect('subscription_plans')

    # Validated payment -> activate subscription
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, owner=request.user)

    # Replace existing subscription or create new
    subscription, created = Subscription.objects.get_or_create(restaurant=restaurant)
    subscription.plan = plan
    subscription.activate()  # sets start/end/is_active
    subscription.save()

    # NOTE: We verify but do not persist detailed payment metadata because models are unchanged.
    # If you want to persist payment_id/order_id/signature, see recommended addition below.

    # Clear session
    try:
        del request.session['subscription_order']
    except KeyError:
        pass

    messages.success(request, f"Subscription activated! Valid until {subscription.end_date.date()}")
    return redirect('dashboard')


# Class-based views (small fixes)
class SubscriptionCreateView(CreateView):
    model = Subscription
    fields = ['plan']  # removed payment_status field because model doesn't have it
    template_name = 'subscription/subscribe.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        # enforce restaurant ownership
        form.instance.restaurant = get_object_or_404(Restaurant, owner=self.request.user)
        return super().form_valid(form)


class SubscriptionDetailView(DetailView):
    model = Subscription
    template_name = 'subscription/subscription_detail.html'
    context_object_name = 'subscription'  # so template can use 'subscription'


class SubscriptionCancelView(View):
    def post(self, request, pk):
        # Only allow the restaurant owner to cancel their subscription
        subscription = get_object_or_404(Subscription, pk=pk, restaurant__owner=request.user)
        subscription.is_active = False
        subscription.save()
        messages.success(request, "Subscription cancelled.")
        return redirect('dashboard')
