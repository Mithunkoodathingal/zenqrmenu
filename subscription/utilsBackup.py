# # subscription/utils.py

# from django.utils import timezone
# from subscription.models import Subscription, SubscriptionPlan
# # from restaurant.models import Restaurant
# from datetime import timedelta

# def ensure_free_subscription(user, restaurant):
#     free_plan = SubscriptionPlan.objects.get(name="Free")

#     if not free_plan:
#         raise Exception("Free plan not configured")

#     subscription = Subscription.objects.filter(
#             user=user,
#             restaurant=restaurant
#         ).first()

#     # ✅ If no subscription → create properly
#     if not subscription:
#         subscription = Subscription.objects.create(
#             user=user,
#             restaurant=restaurant,
#             plan=free_plan,
#             start_date=timezone.now(),
#             end_date=timezone.now() + timedelta(days=365),
#             is_active=True,
#             was_free_trial=True,
#         )
#         return subscription

#     # ✅ FIX: ALWAYS ensure restaurant is linked
#     if subscription.restaurant != restaurant:
#         subscription.restaurant = restaurant

#     # ✅ FIX: ensure free plan if missing
#     if not subscription.plan:
#         subscription.plan = free_plan

#     # ✅ FIX: ensure active
#     if not subscription.is_active:
#         subscription.is_active = True

#     subscription.save()

#     return subscription


# def check_subscription_access(restaurant):
#     subscription = Subscription.objects.filter(
#         restaurant=restaurant,
#         is_active=True,
#     ).select_related("plan").first()

#     if not subscription:
#         return False, "No active subscription"

#     return True, subscription.plan

# def check_subscription_access(user):

# # >>>>>>> parent of 6ee5b35 (fix: Onboarding order minor fix)

#     subscription = Subscription.objects.filter(
#         restaurant=restaurant,
#         is_active=True,
#     ).select_related("plan").first()

#     if not subscription:
#         return False, "No active subscription"

#     if not subscription.is_active:
#         return False, "Subscription inactive"

#     if not subscription.end_date or subscription.end_date < timezone.now():
#         return False, "Subscription expired"

#     return True, subscription.plan