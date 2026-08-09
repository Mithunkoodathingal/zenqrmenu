# subscription/views.py
from subscription.models import (
    Subscription,
    SubscriptionPlan,
    PaymentTransaction,
)
import json
import logging
import traceback
from decimal import Decimal
from django.conf import settings
from subscription.utils import has_active_subscription
from django.contrib import messages
from subscription.utils import check_subscription_access
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_POST
from django.views.generic import DetailView
from rest_framework.response import Response
from rest_framework import status
import razorpay
from datetime import timedelta
from django.conf import settings
from restaurant.models import Restaurant
from rest_framework.permissions import IsAuthenticated
from .models import SubscriptionPlan, Subscription, PaymentTransaction
from restaurant.models import Restaurant
from django.http import JsonResponse
from restaurant.views.views import get_user_restaurant

logger = logging.getLogger(__name__)

# initialize razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))



# def subscription_plans(request):
#     default_plans = [
#         {"name": "Free", "price": Decimal("0.00"), "duration_days": 30, "table_limit": 1,
#          "features": "Unlimited scans, unlimited categories & items"},
#         {"name": "Basic", "price": Decimal("100.00"), "duration_days": 30, "table_limit": 10,
#          "features": "Unlimited scans, unlimited categories & items"},
#         {"name": "Standard", "price": Decimal("200.00"), "duration_days": 30, "table_limit": 20,
#          "features": "Unlimited scans, unlimited categories & items"},
#         {"name": "Enterprise", "price": Decimal("500.00"), "duration_days": 30, "table_limit": 100,
#          "features": "Ideal for hotels, unlimited scans, categories & items"},
#     ]

#     for p in default_plans:
#         SubscriptionPlan.objects.get_or_create(name=p["name"], defaults={
#             "price": p["price"],
#             "duration_days": p["duration_days"],
#             "table_limit": p["table_limit"],
#             "features": p["features"],
#         })

#     plans = SubscriptionPlan.objects.all().order_by('price', 'id')
#     return render(request, 'subscription/subscription_plans.html', {'plans': plans})


# @login_required
# def create_subscription(request, plan_id):
#     """
#     Create a subscription order. For free plans activate immediately.
#     For paid plans:
#       - create a Subscription record (not active yet)
#       - create a Razorpay order
#       - create a PaymentTransaction linked to the Subscription (and store the chosen plan there)
#       - render payment page (JS will call /subscription/payment-success/ on checkout success)
#     """
#     plan = get_object_or_404(SubscriptionPlan, id=plan_id)
#     restaurant = get_object_or_404(Restaurant, owner=request.user)
#     auto_renew = bool(request.POST.get('auto_renew', False))

#     # Free plan -> immediate activation
#     if plan.price == Decimal("0.00"):
#         previous_free = False
#         if hasattr(Subscription, 'was_free_trial'):
#             previous_free = Subscription.objects.filter(restaurant=restaurant, was_free_trial=True).exists()
#         else:
#             previous_free = Subscription.objects.filter(restaurant=restaurant, plan__price=Decimal("0.00")).exists()

#         if previous_free:
#             messages.error(request, "Free plan already used for this restaurant. Choose a paid plan or contact support.")
#             return redirect('subscription:subscription_plans')

#         subscription, created = Subscription.objects.filter(user=request.user)
#         # Ensure stale plan doesn't stay on the subscription (could be from an earlier try).
#         # We will only attach the plan after successful payment (tx.plan is authoritative).
#         if subscription.plan is not None:
#             subscription.plan = None
#             subscription.save()
#         # Do NOT assign subscription.plan yet — wait until payment successful
#         if hasattr(subscription, 'auto_renew'):
#             subscription.auto_renew = auto_renew


#         messages.success(request, f"Free plan activated. Valid until {subscription.end_date.date()}")
#         return redirect('dashboard')

#     # Paid plan -> create/prepare subscription record and Razorpay order
#     subscription, created = Subscription.objects.filter(user=request.user)
#     # Do NOT assign subscription.plan yet — wait until payment successful
#     if hasattr(subscription, 'auto_renew'):
#         subscription.auto_renew = auto_renew
#     # Don't save plan/start/end/is_active here.

#     # Build Razorpay order
#     order_amount_paisa = int(plan.price * Decimal(100))
#     order_currency = 'INR'
#     order_data = {
#         "amount": order_amount_paisa,
#         "currency": order_currency,
#         "payment_capture": 1,
#     }
#     logger.debug("Creating Razorpay order: %s", order_data)
#     order = razorpay_client.order.create(data=order_data)
#     order_id = order.get('id')

#     # Persist PaymentTransaction. Store the chosen plan on the transaction (so we can recover it on success)
#     amount_decimal = (Decimal(order_amount_paisa) / Decimal(100)).quantize(Decimal("0.01"))
#     tx = PaymentTransaction.objects.create(
#         subscription=subscription,
#         plan=plan,
#         razorpay_order_id=order_id,
#         amount=amount_decimal,
#         currency=order_currency,
#         status='created'
#     )

#     # Store minimal context in session (fallback, used by the browser-return)
#     request.session['subscription_order'] = {
#         'order_id': order_id,
#         'payment_tx_id': tx.id,
#         'plan_id': plan.id,
#         'restaurant_id': restaurant.id,
#         'auto_renew': auto_renew,
#     }

#     # amount_paisa is an int (paisa). Prepare a visible rupee string for template.
#     amount_display = f"{(order_amount_paisa / 100):.2f}"  # e.g. 15000 -> "150.00"

#     return render(request, 'subscription/payment.html', {
#         'plan': plan,
#         'order_id': order_id,
#         'amount_paisa': order_amount_paisa,
#         'amount_display': amount_display,
#         'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', None),
#     })


@csrf_exempt
def payment_success_webhook(request):
    """
    Webhook: verify signature if secret configured, find PaymentTransaction and
    activate subscription idempotently. Logs exceptions in detail for debugging.
    """
    payload = request.body.decode('utf-8') or ''
    signature = request.META.get('HTTP_X_RAZORPAY_SIGNATURE')
    webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', None)

    if webhook_secret:
        try:
            razorpay_client.utility.verify_webhook_signature(payload, signature, webhook_secret)
        except Exception as e:
            logger.warning("Webhook signature verification failed: %s", e)
            return HttpResponseBadRequest("invalid signature")

    try:
        data = json.loads(payload)
    except Exception:
        data = {}

    # Try to extract order_id robustly
    order_id = None
    try:
        order_id = (data.get('payload', {}).get('payment', {}).get('entity', {}).get('order_id'))
    except Exception:
        order_id = None
    if not order_id:
        # also try other common shapes
        order_id = data.get('order_id') or data.get('payload', {}).get('order', {}).get('entity', {}).get('id')

    if not order_id:
        logger.info("Webhook received with no order_id; payload: %s", payload[:200])
        return HttpResponse("ok")

    try:
        tx = PaymentTransaction.objects.filter(razorpay_order_id=order_id).select_related('subscription').first()
        if not tx:
            logger.warning("Webhook: no PaymentTransaction found for order %s", order_id)
            return HttpResponse("ok")

        if tx.status == 'paid':
            logger.info("Webhook: transaction %s already paid", order_id)
            return HttpResponse("ok")

        # Optionally get payment id
        payment_id = data.get('payload', {}).get('payment', {}).get('entity', {}).get('id')
        if payment_id:
            tx.razorpay_payment_id = payment_id

        # Activate subscription in a transaction
        with transaction.atomic():
            subscription = tx.subscription
            if not subscription:
                logger.error("Webhook: transaction %s has no linked subscription", order_id)
                tx.status = 'failed'
                tx.save()
                return HttpResponse("ok")

            # ensure plan exists on subscription; if missing, try to fallback to tx.plan
        # Prefer the plan stored on the transaction (this reflects what was paid)
        plan = tx.plan or subscription.plan
        if not plan:
            logger.warning("Webhook: no plan on transaction or subscription. Cannot compute duration.")
            tx.status = 'failed'
            tx.save()
            return HttpResponse("ok")

        # Attach the chosen (paid) plan to the subscription if not already set
        if subscription.plan != plan:
            subscription.plan = plan
            subscription.save()


            # Activate
            if hasattr(subscription, 'activate'):
                try:
                    subscription.activate(mark_free_trial=False)
                except TypeError:
                    # Some older activate(...) signatures may not accept keyword
                    subscription.activate(False)
            else:
                now = timezone.now()
                subscription.start_date = now
                subscription.end_date = now + timezone.timedelta(days=getattr(plan, 'duration_days', 30))
                subscription.is_active = True
                subscription.save()

            tx.status = 'paid'
            if hasattr(tx, 'processed_at'):
                try:
                    tx.processed_at = timezone.now()
                except Exception:
                    # processed_at may not exist on older schemas; ignore
                    pass
            tx.save()

        logger.info("Webhook: activated subscription %s for order %s", subscription.id, order_id)
        return HttpResponse("ok")

    except Exception as exc:
        # Very detailed logging for debugging
        logger.exception("Webhook processing error for order %s: %s\n%s", order_id, exc, traceback.format_exc())
        return HttpResponseBadRequest("processing error")


@require_POST
@csrf_protect
def payment_success_return(request):
    """
    Client-return: verify signature, find tx, mark paid, activate subscription.
    Robustly handles Subscription.activate() variants (with/without mark_free_trial).
    """
    razorpay_order_id = request.POST.get('razorpay_order_id')
    razorpay_payment_id = request.POST.get('razorpay_payment_id')
    razorpay_signature = request.POST.get('razorpay_signature')

    logger.debug("payment_success_return POST: order=%s payment=%s", razorpay_order_id, razorpay_payment_id)

    if not (razorpay_order_id and razorpay_payment_id and razorpay_signature):
        logger.warning("payment_success_return missing fields: %s", request.POST.dict())
        return HttpResponseBadRequest("missing payment fields")

    # Verify Razorpay signature for checkout
    try:
        razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        })
    except Exception as e:
        logger.warning("Payment signature verification failed: %s", e)
        return HttpResponseBadRequest("invalid signature")

    # Find PaymentTransaction via session or order id
    order_ctx = request.session.get('subscription_order', {})
    tx = None
    if order_ctx.get('payment_tx_id'):
        tx = PaymentTransaction.objects.filter(id=order_ctx['payment_tx_id']).select_related('subscription').first()
    if not tx:
        tx = PaymentTransaction.objects.filter(razorpay_order_id=razorpay_order_id).select_related('subscription').first()

    if not tx:
        logger.error("payment_success_return: no PaymentTransaction for order %s session=%s", razorpay_order_id, order_ctx)
        return HttpResponseBadRequest("order mapping missing")

    # If already paid, show success
    if tx.status == 'paid':
        subscription = tx.subscription
        return render(request, 'subscription/success.html', {
            'subscription': subscription,
            'payment_id': tx.razorpay_payment_id or razorpay_payment_id,
            'order_id': tx.razorpay_order_id or razorpay_order_id,
        })

    # Update tx and activate subscription
    try:
        with transaction.atomic():
            tx.razorpay_payment_id = razorpay_payment_id
            tx.razorpay_signature = razorpay_signature
            tx.status = 'paid'
            tx.save()

            subscription = tx.subscription
            if not subscription:
                logger.error("payment_success_return: tx has no subscription: tx=%s", tx.id)
                return HttpResponseBadRequest("no subscription linked to transaction")

            # Prefer the plan recorded on the transaction (source of truth), fallback to subscription.plan
            plan = tx.plan or subscription.plan
            if not plan:
                logger.error("payment_success_return: no plan available on transaction or subscription; tx=%s", tx.id)
                return HttpResponseBadRequest("subscription has no plan")

            # Attach the chosen plan to the subscription if needed
            if subscription.plan != plan:
                subscription.plan = plan
                subscription.save()


            # Try calling activate with mark_free_trial if supported, otherwise call without args
            try:
                subscription.activate(mark_free_trial=False)
            except TypeError:
                # activate() doesn't accept mark_free_trial — call without it
                try:
                    subscription.activate(False)
                except Exception:
                    # fallback to manual activation
                    now = timezone.now()
                    subscription.start_date = now
                    subscription.end_date = now + timezone.timedelta(days=getattr(plan, 'duration_days', 30))
                    subscription.is_active = True
                    subscription.save()
            except AttributeError:
                # No activate method — do manual activation
                now = timezone.now()
                subscription.start_date = now
                subscription.end_date = now + timezone.timedelta(days=getattr(plan, 'duration_days', 30))
                subscription.is_active = True
                subscription.save()
    except Exception as exc:
        logger.exception("payment_success_return activation failed for order %s: %s", razorpay_order_id, exc)
        messages.error(request, "Payment received but activation failed. Our team has been notified; please contact support.")
        return render(request, 'subscription/error_activation.html', {
            'reason': str(exc),
            'order_id': razorpay_order_id,
            'payment_id': razorpay_payment_id,
        })

    # Clear session mapping
    try:
        del request.session['subscription_order']
    except KeyError:
        pass

    return render(request, 'subscription/success.html', {
        'subscription': subscription,
        'payment_id': razorpay_payment_id,
        'order_id': razorpay_order_id,
    })


# class SubscriptionDetailView(DetailView):
#     model = Subscription
#     template_name = 'subscription/subscription_detail.html'
#     context_object_name = 'subscription'


class SubscriptionCancelView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        pk = self.kwargs.get('pk')
        subscription = get_object_or_404(Subscription, pk=pk)
        return subscription.restaurant.owner == self.request.user

    def post(self, request, pk):
        subscription = get_object_or_404(Subscription, pk=pk, restaurant__owner=request.user)
        now = timezone.now()
        if hasattr(subscription, 'is_cancelled'):
            subscription.is_cancelled = True
        if hasattr(subscription, 'auto_renew'):
            subscription.auto_renew = False
        if hasattr(subscription, 'cancelled_at'):
            subscription.cancelled_at = now
        subscription.save()
        messages.success(request, "Subscription cancelled. Access will continue until period end.")
        return redirect('dashboard')

    def get(self, request, *args, **kwargs):
        messages.error(request, "Invalid request method.")
        return redirect('dashboard')


def require_active_subscription(request, restaurant):
    try:
        subscription = restaurant.subscription
        if not subscription.has_active_subscription():
            return render(
                request,
                "subscription/expired.html",
                {"restaurant": restaurant},
                status=403
            )
    except Subscription.DoesNotExist:
        return render(
            request,
            "subscription/expired.html",
            {"restaurant": restaurant},
            status=403
        )

    return None


##############  API ENDPOINTS #################

def subscription_plans_api(request):
    plans = SubscriptionPlan.objects.all().order_by('price')

    data = []
    for p in plans:
        data.append({
            "id": p.id,
            "name": p.name,
            "price": float(p.price),
            "duration_days": p.duration_days,
            "table_limit": p.table_limit,
            "features": [f.strip() for f in p.features.split(",")],  # ✅ FIX
        })

    return JsonResponse({"plans": data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_create_subscription(request):

    try:

        plan_id = request.data.get("plan_id")

        if not plan_id:
            return Response(
                {
                    "success": False,
                    "error": "plan_id is required"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # =====================================================
        # GET PLAN
        # =====================================================

        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)

        except SubscriptionPlan.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": "Invalid plan"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user

        # =====================================================
        # GET RESTAURANT
        # =====================================================

        restaurant = Restaurant.objects.filter(
            owner=user
        ).first()

        if not restaurant:
            return Response(
                {
                    "success": False,
                    "error": "Create restaurant first"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # =====================================================
        # REMOVE BROKEN SUBSCRIPTIONS
        # =====================================================

        Subscription.objects.filter(
            restaurant=restaurant,
            plan__isnull=True
        ).delete()

        # =====================================================
        # GET CURRENT ACTIVE SUBSCRIPTION
        # =====================================================

        active_subscription = (
            Subscription.objects
            .filter(
                restaurant=restaurant,
                is_active=True,
                plan__isnull=False
            )
            .select_related("plan")
            .order_by("-id")
            .first()
        )

        # =====================================================
        # PREVENT PAID -> FREE DOWNGRADE
        # =====================================================

        if (
            active_subscription and
            active_subscription.plan and
            active_subscription.plan.price > 0 and
            plan.price == 0
        ):

            return Response(
                {
                    "success": False,
                    "error": "Cannot downgrade to free plan"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # =====================================================
        # DEACTIVATE OLD SUBSCRIPTIONS
        # =====================================================

        # Subscription.objects.filter(
        #     restaurant=restaurant
        # ).update(
        #     is_active=False
        # )

        # =====================================================
        # CREATE DATES
        # =====================================================

        start_date = timezone.now()

        end_date = (
            start_date +
            timedelta(days=plan.duration_days)
        )

        # =====================================================
        # FREE PLAN
        # =====================================================

        if plan.price == 0:

            subscription = Subscription.objects.get(
            user=user,
            restaurant=restaurant
        )

            logger.info(
                f"FREE PLAN ACTIVATED | "
                f"user={user.id} | "
                f"restaurant={restaurant.id}"
            )

            return Response({
                "success": True,
                "free": True,
                "message": "Free plan activated",
                "subscription": {
                    "id": subscription.id,
                    "plan": plan.name,
                    "price": str(plan.price),
                    "is_active": True,
                    "start_date": subscription.start_date,
                    "end_date": subscription.end_date,
                    "table_limit": plan.table_limit,
                    "menu_item_limit": plan.menu_item_limit,
                }
            })

        # =====================================================
        # PAID PLAN
        # =====================================================

        order_amount = int(plan.price * 100)

        order = razorpay_client.order.create({
            "amount": order_amount,
            "currency": "INR",
            "payment_capture": 1,

            "notes": {
                "user_id": str(user.id),
                "restaurant_id": str(restaurant.id),
                "restaurant_name": restaurant.name,
                "email": user.email,
                "phone": restaurant.phone,
                "plan": plan.name,
            }
        })

        subscription = Subscription.objects.get(
            user=user,
            restaurant=restaurant
        )

        # =====================================================
        # PAYMENT TRANSACTION
        # =====================================================

        PaymentTransaction.objects.create(
            subscription=subscription,
            plan=plan,
            razorpay_order_id=order["id"],
            amount=plan.price,
            currency="INR",
            status="created"
        )

        logger.info(
            f"PAID PLAN CREATED | "
            f"user={user.id} | "
            f"restaurant={restaurant.id} | "
            f"plan={plan.name}"
        )

        return Response({
            "success": True,
            "order_id": order["id"],
            "amount": order_amount,
            "key": settings.RAZORPAY_KEY_ID,
            "plan": plan.name,
            "subscription_id": subscription.id,

            "prefill": {
                "name": restaurant.name,
                "email": user.email,
                "contact": restaurant.phone,
            }
        })
    

    except Exception as e:

        logger.exception(
            "Subscription API error"
        )

        return Response(
            {
                "success": False,
                "error": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_verify_payment(request):

    order_id = request.data.get("razorpay_order_id")
    payment_id = request.data.get("razorpay_payment_id")
    signature = request.data.get("razorpay_signature")

    if not (order_id and payment_id and signature):
        return JsonResponse({
            "success": False,
            "error": "Missing payment data"
        }, status=400)

    # ✅ Verify signature
    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        })
    except Exception:
        return JsonResponse({
            "success": False,
            "error": "Invalid signature"
        }, status=400)

    try:
        tx = PaymentTransaction.objects.select_related("subscription", "plan").get(
            razorpay_order_id=order_id
        )
    except PaymentTransaction.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Transaction not found"
        }, status=404)

    # 🔒 SECURITY: ensure this payment belongs to current user
    if tx.subscription.user != request.user:
        return JsonResponse({
            "success": False,
            "error": "Unauthorized transaction"
        }, status=403)

    # 🔁 Prevent duplicate activation
    if tx.status == "paid":
        return JsonResponse({"success": True})

    subscription = tx.subscription
    plan = tx.plan

    # ✅ Activate subscription ONLY now
    subscription.plan = plan
    subscription.activate()

    # ✅ Update transaction
    tx.status = "paid"
    tx.razorpay_payment_id = payment_id
    tx.save()

    return JsonResponse({
        "success": True,
        "message": "Subscription activated successfully"
    })



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription_status(request):

    Subscription.objects.filter(
        is_active=True,
        end_date__lte=timezone.now()
    ).update(
        is_active=False
    )

    subscription = (
        Subscription.objects
        .filter(user=request.user, is_active=True)
        .select_related("plan")
        .first()
    )

    if subscription:

        # Auto-expire subscription
        if subscription.end_date and subscription.end_date <= timezone.now():
            subscription.is_active = False
            subscription.save()

            subscription = None

    if not subscription:
        return Response({
            "has_subscription": False
        })


    return Response({
        "debug": True,
        "subscription_exists": bool(subscription),
        "is_active": subscription.is_active if subscription else False,
        "has_subscription": True,
        "plan": subscription.plan.name if subscription.plan else None,
        "plan_id": subscription.plan.id if subscription.plan else None,
        "price": str(subscription.plan.price),
        "table_limit": subscription.plan.table_limit,
    })




def ensure_free_subscription(user, restaurant):
    free_plan = SubscriptionPlan.objects.filter(price=0).first()

    if not free_plan:
        raise Exception("Free plan not configured")

    sub, created = Subscription.objects.get_or_create(
        user=user,
        defaults={
            "restaurant": restaurant,
            "plan": free_plan,
        }
    )

    if not sub.is_active:
        sub.plan = free_plan
        sub.start_date = timezone.now()
        sub.end_date = timezone.now() + timezone.timedelta(days=3650)
        sub.is_active = True
        sub.save()

    return sub
#=========================revert to specific commit===============