# restaurant/views.py

import json
import logging
import os
import traceback
from decimal import Decimal, InvalidOperation
import datetime
from django.db.models import Prefetch 
import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from allauth.account.views import SignupView
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseServerError,
    JsonResponse,
)

from django.core.files import File
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from allauth.account.models import EmailAddress, EmailConfirmation
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.db import IntegrityError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.decorators import api_view, permission_classes, parser_classes
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, DecimalField, ExpressionWrapper, Q
import datetime
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
import time
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from io import BytesIO
from django.core.files import File
from django.http import JsonResponse
from subscription.utils import check_subscription_access, ensure_free_subscription
from django.contrib.auth.models import User
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from allauth.account.forms import ResetPasswordForm
from allauth.account.adapter import get_adapter
from rest_framework import viewsets, status
from .serializers import OrderSerializer
from .serializers import RestaurantSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_page
from django.utils.translation import gettext as _
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import CreateView, UpdateView, DeleteView
from django.core.mail import EmailMultiAlternatives, send_mail
from django.contrib.sessions.middleware import SessionMiddleware
from django.conf import settings
from django.urls import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .forms import SignupForm
from .forms import FoodItemForm
from django.utils import timezone
from django.http import JsonResponse
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from .models import (
    Restaurant,
    Table,
    Category,
    FoodItem,
    Order,
    OrderItem,
    AddOn,
)

from subscription.models import Subscription
import traceback
from allauth.account.models import EmailAddress

logger = logging.getLogger(__name__)

User = get_user_model()

# cooldown in seconds to avoid spamming resend per email (adjust as you like)
RESEND_COOLDOWN_SECONDS = 120  # 2 minutes



@require_POST
def confirm_order_ajax(request, order_id):
    """
    Mark the order as *sent to kitchen* but do NOT mark it completed.
    This keeps the order visible in the kitchen interface (which lists is_completed=False).
    Returns totals and a success JSON.
    """
    order = get_object_or_404(Order, id=order_id)

    # Log who called it and timestamps
    caller = request.user.id if request.user.is_authenticated else "anon"
    logger.info("confirm_order_ajax called by user=%s for order=%s (created_at=%s now=%s)",
                caller, order_id, order.created_at, timezone.now())

    try:
        # Do NOT set order.is_completed = True here.
        # Optionally you can add an audit field like order.sent_to_kitchen = True and save(),
        # but to keep schema unchanged we will just log the action and return success.
        logger.info("Order %s marked as 'sent to kitchen' (logical) by user=%s", order.id, caller)

        total_price = 0.0
        total_count = 0
        for it in order.order_items.select_related('food_item').prefetch_related('selected_addons').all():
            base = float(it.food_item.price or 0) * (it.quantity or 0)
            addons_price = float(sum(a.price for a in it.selected_addons.all()) or 0) * (it.quantity or 0)
            total_price += base + addons_price
            total_count += (it.quantity or 0)

        return JsonResponse({
            'success': True,
            'order_id': order.id,
            'items_count': total_count,
            'total_price': float(total_price),
            'message': 'Order sent to kitchen (logical).'
        })
    except Exception as exc:
        tb = traceback.format_exc()
        logger.exception("confirm_order_ajax failed for order=%s: %s", order_id, exc)
        if settings.DEBUG:
            return JsonResponse({'success': False, 'message': 'Server error', 'traceback': tb}, status=500)
        return JsonResponse({'success': False, 'message': 'Server error'}, status=500)


@login_required
def complete_order(request, order_id):
    """
    Mark the order finished/completed. This *is* the action that sets is_completed=True
    so the kitchen will stop showing the order.
    Only allow a restaurant owner / staff member who owns the restaurant to mark completion.
    """
    # Restrict to restaurant owner (or use your staff check)
    order = get_object_or_404(Order, id=order_id, table__restaurant=request.user.restaurant)

    logger.info("complete_order called by user=%s for order=%s", request.user.id, order_id)
    order.is_completed = True
    order.save()
    return JsonResponse({'success': True, 'order_id': order.id})



# -----------------------
# Email / helpers
# -----------------------
def send_welcome_email(user):
    """
    Send plain+HTML welcome email to newly registered user.
    Uses settings.EMAIL_* configuration.
    """
    subject = "Welcome to Zen QR Menu!"
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@localhost')
    to_email = [user.email]

    # plain text body
    text_content = render_to_string('emails/welcome_email.txt', {
        'user': user,
        'site_name': getattr(settings, 'SITE_NAME', 'Zen Menu'),
    })

    # html body
    html_content = render_to_string('emails/welcome_email.html', {
        'user': user,
        'site_name': getattr(settings, 'SITE_NAME', 'Zen Menu'),
        'login_url': (getattr(settings, 'SITE_DOMAIN', '') + reverse('login')) if getattr(settings, 'SITE_DOMAIN', '') else reverse('login')
    })

    msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)


# -----------------------
# Signup views
# -----------------------
def signup_view(request):
    """
    Simple signup view using SignupForm. Stores signup email in session
    so the thank-you page can present and resend confirmation.
    """
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # save the user via the form contract (pass request so confirmation is sent)
                    result = None
                    if hasattr(form, "try_save"):
                        result = form.try_save(request)
                    else:
                        result = form.save(request)

                    # normalize result to user object
                    user_obj = result[0] if isinstance(result, tuple) else result

                    # store the signup email in session so thankyou page can resend if needed
                    email = (form.cleaned_data.get('email') or '').strip()
                    if email:
                        request.session['signup_email'] = email

                    messages.success(request, "Account created. A confirmation email has been sent — check your inbox.")
                return redirect('signup_thankyou')
            except Exception as exc:
                logger.exception("Signup transaction failed: %s", exc)
                messages.error(request, "Server error while creating account.")
                return render(request, 'account/signup.html', {'form': form})
        else:
            # invalid: render with errors
            return render(request, 'account/signup.html', {'form': form})
    else:
        form = SignupForm()
    return render(request, 'account/signup.html', {'form': form})


class MySignupView(SignupView):
    """
    Custom signup view that uses the allauth form contract but always redirects
    to a friendly 'signup_thankyou' page. Stores signup email in session.
    """
    form_class = SignupForm
    success_url = reverse_lazy('signup_thankyou')

    def form_valid(self, form):
        email = (form.cleaned_data.get('email') or '').strip()

        # If there is an EmailAddress row and it's unverified -> resend and redirect
        existing_ea = EmailAddress.objects.filter(email__iexact=email).first()
        if existing_ea and not existing_ea.verified:
            try:
                existing_ea.send_confirmation(self.request)
                # Save email in session for thank-you page
                if email:
                    self.request.session['signup_email'] = email
                messages.success(self.request, "A confirmation email has been resent. Check your inbox.")
            except Exception:
                messages.info(self.request, "If an account exists with that email, a confirmation was (attempted) sent.")
            return redirect(self.get_success_url())

        # Otherwise create user via form and send confirmation (form.save(request) should do it)
        try:
            with transaction.atomic():
                if hasattr(form, "try_save"):
                    result = form.try_save(self.request)
                else:
                    result = form.save(self.request)

                user_obj = result[0] if isinstance(result, tuple) else result

                # Ensure session has the email for the thank-you page
                if email:
                    self.request.session['signup_email'] = email

        except Exception as exc:
            logger.exception("Error while saving signup form: %s", exc)
            # Fallback to parent behaviour if something unexpected occurs
            return super().form_valid(form)

        messages.success(self.request, "Account created. Check your email for a confirmation link.")
        return redirect(self.get_success_url())


# -----------------------
# Resend confirmation (logged-in and public)
# -----------------------
@login_required
def resend_confirmation(request):
    try:
        email_address = EmailAddress.objects.filter(user=request.user).order_by('-primary').first()
        if email_address:
            email_address.send_confirmation(request)
            messages.success(request, "Confirmation email resent. Please check your inbox.")
        else:
            messages.error(request, "No email address found for your account.")
    except Exception:
        messages.error(request, "Could not resend confirmation. Try again later.")
    return redirect('dashboard')


@require_POST
def resend_confirmation_by_email(request):
    """
    Public view: POST 'email' (or falls back to session 'signup_email').
    Sends a fresh allauth confirmation email if an EmailAddress exists.
    Generic success message to avoid account enumeration.
    Throttled per email using the session.
    """
    logger.info("resend_confirmation_by_email called. POST keys=%s session_keys=%s", list(request.POST.keys()), list(request.session.keys()))
    # Defensive: ensure session exists
    if not hasattr(request, 'session'):
        try:
            SessionMiddleware(lambda r: None).process_request(request)
        except Exception:
            logger.exception("Failed to ensure session in resend view")

    # Defensive: ensure session exists
    if not hasattr(request, 'session'):
        try:
            SessionMiddleware(lambda r: None).process_request(request)
        except Exception:
            pass

    email = (request.POST.get('email') or request.session.get('signup_email') or '').strip()
    if not email:
        messages.error(request, "Please provide an email address.")
        logger.info("Resend request missing email. POST keys=%s", list(request.POST.keys()))
        return redirect('login')

    # throttle key
    session_key = f"resend_confirmation_last_sent:{email.lower()}"
    last_sent = request.session.get(session_key, 0)
    now = int(time.time())
    if now - last_sent < RESEND_COOLDOWN_SECONDS:
        wait = RESEND_COOLDOWN_SECONDS - (now - last_sent)
        messages.info(request, f"A confirmation was sent recently. Please wait {wait} seconds before trying again.")
        return redirect('login')

    try:
        ea = EmailAddress.objects.filter(email__iexact=email).first()
        if ea:
            try:
                sent_obj = ea.send_confirmation(request)  # create+send new confirmation
                logger.info("Resent confirmation for %s -> %r", email, sent_obj)
                messages.success(request, "A confirmation email has been sent. Check your inbox and spam folder.")
                # record time of send in session to throttle
                if email:
                    request.session['signup_email'] = email
                    request.session.modified = True
            except Exception as exc:
                logger.exception("Failed to send confirmation for %s: %s", email, exc)
                messages.error(request, "Could not send confirmation email at the moment. Try again later.")
        else:
            # Generic message (avoid revealing whether the email exists)
            messages.success(request, "If an account exists with that email, a confirmation email has been sent.")
            logger.info("Resend requested for non-existing email: %s", email)
    except Exception as exc:
        logger.exception("Unexpected error in resend_confirmation_by_email for %s: %s", email, exc)
        messages.error(request, "Unable to process your request. Try again later.")

    # Clear signup_email from session to avoid reuse (optional)
    request.session.pop('signup_email', None)
    return redirect('login')


def signup_thankyou(request):
    """
    Friendly thank-you page after signup.
    Reads 'signup_email' from session and passes it to template so the
    'Resend confirmation' hidden input can use it safely.
    """
    signup_email = request.session.get('signup_email', '')
    return render(request, 'account/signup_thankyou.html', {'signup_email': signup_email})


def terms_conditions(request):
    return render(request, 'restaurant/terms.html')



# -----------------------
# Authentication helpers (login/logout)
# -----------------------


def _user_has_verified_email(user):
    if not user:
        return False
    return EmailAddress.objects.filter(user=user, verified=True).exists()

# paste this whole function (replace the existing login_view)
def login_view(request):
    """
    Robust login view:
    - Accepts both 'username' (Django) and 'login' (allauth).
    - Shows resend confirmation UI when an unverified email exists.
    - Always provides `signup_email` and `unverified_email` in template context to avoid VariableDoesNotExist.
    """
    COOLDOWN_SECONDS = 300

    # Always pull signup_email from session safely so templates can reference it
    signup_email = request.session.get("signup_email")
    # ensure unverified_email exists (may be set later)
    unverified_email = None

    # helper to render with the guaranteed context
    def safe_render(template_name, extra_context=None, status=200):
        ctx = {"signup_email": signup_email, "unverified_email": unverified_email}
        if extra_context:
            ctx.update(extra_context)
        return render(request, template_name, ctx, status=status)

    # GET -> show blank form; pass any session signup_email so the template can show resend UI
    if request.method != "POST":
        form = AuthenticationForm(request=request)
        # prefer explicit unverified email saved in session from signup flow
        unverified_email = signup_email or None
        return safe_render("account/login.html", {"form": form})

    # POST branch
    form = AuthenticationForm(request=request, data=request.POST)

    # support both names used in templates
    username_or_email = (request.POST.get("username") or request.POST.get("login") or "").strip()
    password = request.POST.get("password", "")

    if not username_or_email:
        form.add_error("username", _("Please enter your username or email."))
        return safe_render("account/login.html", {"form": form})

    # First try normal authenticate (this returns a user if allowed by backends)
    user = authenticate(request, username=username_or_email, password=password)

    possible_user = None
    if user is None:
        # try email lookup -> check password locally (but don't log in yet)
        try:
            possible_user = User.objects.get(email__iexact=username_or_email)
        except User.DoesNotExist:
            possible_user = None

        # if no email match, try username lookup
        if not possible_user:
            try:
                possible_user = User.objects.get(username__iexact=username_or_email)
            except User.DoesNotExist:
                possible_user = None

        # If we found a user and password matches, we'll handle unverified/inactive cases
        if possible_user and not possible_user.check_password(password):
            # wrong password
            form.add_error("password", _("Incorrect password. Please try again."))
            return safe_render("account/login.html", {"form": form})

        if not possible_user:
            form.add_error("username", _("No account found with this username or email."))
            return safe_render("account/login.html", {"form": form})

    # If user is None but possible_user exists and password matched -> handle unverified email
    if user is None and possible_user:
        # If email is not verified -> resend (throttled) and present the resend UI
        if not _user_has_verified_email(possible_user):
            ea = EmailAddress.objects.filter(user=possible_user).order_by("-primary").first()
            unverified_email = ea.email if ea else possible_user.email
            session_key = f"last_confirmation_sent:{unverified_email.lower()}"
            last_sent = request.session.get(session_key, 0)
            now = int(time.time())
            if now - last_sent >= COOLDOWN_SECONDS:
                try:
                    # try to create/send confirmation (best effort)
                    if ea:
                        ea.send_confirmation(request)
                    else:
                        ea, created = EmailAddress.objects.get_or_create(
                            user=possible_user,
                            email=possible_user.email,
                            defaults={"verified": False, "primary": True},
                        )
                        if ea:
                            try:
                                ea.send_confirmation(request)
                            except Exception:
                                logger.exception("Error sending confirmation to %s", possible_user.email)
                    request.session[session_key] = now
                    request.session.modified = True
                    messages.success(request, _("A confirmation email has been sent. Check your inbox and spam folder."))
                except Exception:
                    logger.exception("Failed to send confirmation for %s", unverified_email)
                    messages.info(request, _("If an account exists with that email, a confirmation was (attempted) sent."))
            else:
                wait = COOLDOWN_SECONDS - (now - last_sent)
                messages.info(request, _("A confirmation email was recently sent. Please wait %(seconds)d seconds.") % {"seconds": wait})

            form.add_error(None, _("Your email address is not verified. Please check your email for the confirmation link."))
            form.add_error("username", _("Account exists but email not verified."))
            # pass unverified_email and signup_email so template shows the resend UI
            return safe_render("account/login.html", {"form": form})

        # If email verified but user inactive -> activate and retry authenticate
        if not possible_user.is_active and _user_has_verified_email(possible_user):
            possible_user.is_active = True
            possible_user.save(update_fields=["is_active"])
            # attempt authenticate again
            user = authenticate(request, username=possible_user.username, password=password)

    # If we have a valid user, log them in
    if user is not None:
        if not user.is_active:
            form.add_error(None, _("Account is inactive."))
            return safe_render("account/login.html", {"form": form})
        login(request, user)
        messages.success(request, _("Logged in successfully."))
        next_url = request.POST.get("next") or request.GET.get("next") or reverse_lazy("dashboard")
        return redirect(next_url)

    # fallback — invalid credentials
    form.add_error(None, _("Invalid credentials. Please try again."))
    return safe_render("account/login.html", {"form": form})


class CustomLogoutView(View):
    """Simple logout view that supports GET and POST and redirects to login."""
    def post(self, request):
        logout(request)
        return redirect("login")

    def get(self, request):
        logout(request)
        return redirect("login")





# -----------------------
# TableCreateView (with subscription guard)
# -----------------------
# class TableCreateView(LoginRequiredMixin, CreateView):
#     model = Table
#     fields = ['table_number']
#     template_name = 'restaurant/table_form.html'
#     success_url = reverse_lazy('create_table_qr')

#     # restaurant/views.py (inside TableCreateView)

#     def dispatch(self, request, *args, **kwargs):
#         self.restaurant = get_object_or_404(Restaurant, owner=request.user)
#         try:
#             subscription = self.restaurant.subscription
#         except Subscription.DoesNotExist:
#             messages.error(request, "You need an active subscription to create tables.")
#             return redirect("subscription:subscription_plans")


#         # Ensure subscription has a plan attached
#         if not subscription.plan:
#             messages.error(request, "Subscription is missing a plan. Please contact support or re-subscribe.")
#             return redirect("subscription:subscription_plans")

#         # Ensure subscription is active and not expired
#         if not subscription.is_active or (subscription.end_date and subscription.end_date < timezone.now()):
#             messages.error(request, "Your subscription expired. Please renew.")
#             return redirect("subscription:subscription_plans")

#         # Ensure there are remaining table slots
#         if subscription.remaining_tables() <= 0:
#             messages.error(request, "You reached your table limit. Upgrade your plan.")
#             return redirect("subscription:subscription_plans")

#         return super().dispatch(request, *args, **kwargs)


    def form_valid(self, form):
            form.instance.restaurant = self.restaurant

            # Try to validate uniqueness at the model/form level first (optional but helpful)
            try:
                # validate_unique will raise ValidationError if unique constraint violated
                form.instance.validate_unique()
            except ValidationError as e:
                # Attach any field-specific unique errors to the form and re-render
                # e.message_dict is a dict like {'table_number': ['...']}
                for field, msgs in e.message_dict.items():
                    for m in msgs:
                        form.add_error(field, m)
                return self.form_invalid(form)

            # Now attempt to save and catch DB-level IntegrityError as a fallback
            try:
                response = super().form_valid(form)
            except IntegrityError:
                # Defensive: add a friendly error on the table_number field
                form.add_error('table_number', "This table number is already used — please enter a unique number.")
                return self.form_invalid(form)

            # QR generation as before (keep existing behavior)
            try:
                generate_qr_code(self.object)
            except Exception as e:
                messages.warning(self.request, f"QR generation failed: {e}")
            return response



class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    fields = ['name']
    template_name = 'restaurant/category_form.html'
    success_url = reverse_lazy('manage_menu')

    def form_valid(self, form):
        form.instance.restaurant = self.request.user.restaurant
        return super().form_valid(form)


class FoodItemCreateView(LoginRequiredMixin, CreateView):
    model = FoodItem
    form_class = FoodItemForm
    template_name = 'restaurant/fooditem_form.html'
    success_url = reverse_lazy('manage_menu')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['category'].queryset = Category.objects.filter(restaurant=self.request.user.restaurant)
        return form

    def form_valid(self, form):
        category = form.cleaned_data['category']
        if category.restaurant != self.request.user.restaurant:
            messages.error(self.request, "Invalid category selection.")
            return self.form_invalid(form)

        response = super().form_valid(form)

        addon_data = self.request.POST.get('addon_data')
        if addon_data:
            try:
                addon_list = json.loads(addon_data)
                for item in addon_list:
                    name_price = item.split(":")
                    if len(name_price) == 2:
                        name = name_price[0].strip()
                        price = float(name_price[1].strip())
                        addon, _ = AddOn.objects.get_or_create(name=name, price=price)
                        self.object.addons.add(addon)
            except json.JSONDecodeError:
                messages.warning(self.request, "Failed to parse add-ons.")
        return response


class FoodItemUpdateView(LoginRequiredMixin, UpdateView):
    model = FoodItem
    fields = ['category', 'name', 'price', 'description', 'image']
    template_name = 'restaurant/fooditem_form.html'

    def get_success_url(self):
        messages.success(self.request, "Food item updated successfully!")
        return reverse_lazy('manage_menu')

    def form_valid(self, form):
        food_item = form.instance
        if food_item.category.restaurant != self.request.user.restaurant:
            messages.error(self.request, "Unauthorized action.")
            return self.form_invalid(form)
        return super().form_valid(form)


class FoodItemDeleteView(LoginRequiredMixin, DeleteView):
    model = FoodItem
    template_name = 'restaurant/fooditem_confirm_delete.html'

    def get_success_url(self):
        messages.success(self.request, "Food item deleted successfully!")
        return reverse_lazy('manage_menu')

    def delete(self, request, *args, **kwargs):
        food_item = self.get_object()
        if food_item.category.restaurant != self.request.user.restaurant:
            messages.error(self.request, "Unauthorized action.")
            return redirect('manage_menu')
        return super().delete(request, *args, **kwargs)


# -----------------------
# Dashboard / menu
# -----------------------
@login_required
def dashboard(request):
    """
    Dashboard shows subscription summary and scannable QR tiles.
    """
    try:
        restaurant = request.user.restaurant
    except Restaurant.DoesNotExist:
        return render(request, 'restaurant/create_restaurant.html')

    subscription = None
    subscription_active = False
    # allowed_table_limit = 0
    allowed_table_ids = []

    try:
        subscription = restaurant.subscription
        if subscription and subscription.has_active_subscription():
            subscription_active = True
            # allowed_table_limit = subscription.plan.table_limit if subscription.plan else 0
            # first N tables by id are allowed
            allowed_table_ids = list(
                Table.objects.filter(restaurant=restaurant)
                # .order_by('id')[:allowed_table_limit]
                .values_list('id', flat=True)
            )
    except Subscription.DoesNotExist:
        subscription = None

    # All tables for the restaurant
    tables_qs = Table.objects.filter(restaurant=restaurant).order_by('id')
    tables = []
    scannable_tables = []
    for t in tables_qs:
        t.is_scannable = (t.id in allowed_table_ids) and subscription_active
        tables.append(t)
        if t.is_scannable:
            scannable_tables.append(t)

    total_tables_created = tables_qs.count()
    scannable_count = len(scannable_tables)
    remaining_slots = max((allowed_table_limit - total_tables_created), 0) if subscription_active else 0

    categories = Category.objects.filter(restaurant=restaurant)

    context = {
        'restaurant': restaurant,
        'tables': tables,
        'scannable_tables': scannable_tables,      # <-- added
        'categories': categories,
        'subscription': subscription,
        'subscription_active': subscription_active,
        'allowed_table_limit': allowed_table_limit,
        'total_tables_created': total_tables_created,
        'scannable_count': scannable_count,
        'remaining_slots': remaining_slots,
    }
    return render(request, 'restaurant/dashboard.html', context)


# Add near the other views in restaurant/views.py

@login_required
def manage_menu(request):
    """
    Render the Manage Menu page: categories, items, tables list (with scannable badges).
    NOTE: This intentionally does NOT include the subscription summary (dashboard shows that).
    """
    try:
        restaurant = request.user.restaurant
    except Restaurant.DoesNotExist:
        return render(request, 'restaurant/create_restaurant.html')

    # determine subscription + allowed table ids (same logic as dashboard)
    subscription = None
    subscription_active = False
    allowed_table_limit = 0
    allowed_table_ids = []
    try:
        subscription = restaurant.subscription
        if subscription and subscription.has_active_subscription():
            subscription_active = True
            allowed_table_limit = subscription.plan.table_limit if subscription.plan else 0
            allowed_table_ids = list(
                Table.objects.filter(restaurant=restaurant).order_by('id')[:allowed_table_limit]
                .values_list('id', flat=True)
            )
    except Subscription.DoesNotExist:
        subscription = None

    # Tables annotated with is_scannable
    tables_qs = Table.objects.filter(restaurant=restaurant).order_by('id')
    tables = []
    for t in tables_qs:
        t.is_scannable = (t.id in allowed_table_ids) and subscription_active
        tables.append(t)

    total_tables_created = tables_qs.count()
    scannable_count = sum(1 for t in tables if t.is_scannable)
    remaining_slots = max((allowed_table_limit - total_tables_created), 0) if subscription_active else 0

    categories = Category.objects.filter(restaurant=restaurant)

    context = {
        'restaurant': restaurant,
        'tables': tables,
        'categories': categories,
        'subscription': subscription,
        'subscription_active': subscription_active,
        'allowed_table_limit': allowed_table_limit,
        'total_tables_created': total_tables_created,
        'scannable_count': scannable_count,
        'remaining_slots': remaining_slots,
    }
    return render(request, 'restaurant/manage_menu.html', context)


@login_required
def menu_preview(request):
    try:
        restaurant = request.user.restaurant
        tables = Table.objects.filter(restaurant=restaurant)
        categories = Category.objects.filter(restaurant=restaurant).prefetch_related('fooditem_set')
        return render(request, 'restaurant/menu_preview.html', {
            'restaurant': restaurant,
            'tables': tables,
            'categories': categories,
        })
    except Restaurant.DoesNotExist:
        return render(request, 'restaurant/menu_preview.html', {
            'restaurant': None,
            'tables': [],
            'categories': []
        })


# -----------------------
# Public menu view (with subscription guard)
# -----------------------

def _user_is_restaurant_owner(request, restaurant):
    if not request.user.is_authenticated:
        return False
    for field in ('owner', 'user', 'created_by'):
        if getattr(restaurant, field, None) == request.user:
            return True
    try:
        if getattr(request.user, 'restaurant', None) == restaurant:
            return True
    except Exception:
        pass
    return False

# def menu_view(request, restaurant_id, table_id):
#     restaurant = get_object_or_404(Restaurant, id=restaurant_id)
#     table = get_object_or_404(Table, id=table_id, restaurant=restaurant)

#     # subscription / allowed-table checks (unchanged)
#     try:
#             subscription = restaurant.subscription

#             if not subscription.has_active_subscription():
#                 return render(
#                     request,
#                     "subscription/expired.html",
#                     {
#                         "restaurant": restaurant,
#                         "reason": "expired"
#                     },
#                     status=403
#                 )

#             allowed_limit = subscription.plan.table_limit if subscription.plan else 0
#             allowed_table_ids = list(
#                 Table.objects
#                 .filter(restaurant=restaurant)
#                 .order_by('id')[:allowed_limit]
#                 .values_list('id', flat=True)
#             )

#             if table.id not in allowed_table_ids:
#                 return render(
#                     request,
#                     "subscription/expired.html",
#                     {
#                         "restaurant": restaurant,
#                         "reason": "table_limit"
#                     },
#                     status=403
#                 )

#     except Subscription.DoesNotExist:
#             return render(
#                 request,
#                 "subscription/expired.html",
#                 {
#                     "restaurant": restaurant,
#                     "reason": "no_subscription"
#                 },
#                 status=403
#             )


#     is_owner = _user_is_restaurant_owner(request, restaurant)

#     # Prefetch into category.active_items (owner -> all, public -> only not paused)
#     if is_owner:
#         categories = Category.objects.filter(restaurant=restaurant).prefetch_related(
#             Prefetch(
#                 'fooditem_set',
#                 queryset=FoodItem.objects.select_related('category').order_by('id'),
#                 to_attr='active_items'
#             )
#         )
#         food_items = FoodItem.objects.filter(category__restaurant=restaurant).select_related('category').order_by('id')
#     else:
#         categories = Category.objects.filter(restaurant=restaurant).prefetch_related(
#             Prefetch(
#                 'fooditem_set',
#                 queryset=FoodItem.objects.filter(is_paused=False).select_related('category').order_by('id'),
#                 to_attr='active_items'
#             )
#         )
#         food_items = FoodItem.objects.filter(category__restaurant=restaurant, is_paused=False).select_related('category').order_by('id')

#     # Defensive extra-check: if prefetch produced active_items but it somehow contains paused items
#     # or if some categories didn't prefetch correctly, normalize them here for public users.
#     if is_owner:
#         categories = Category.objects.filter(restaurant=restaurant).prefetch_related(
#             Prefetch(
#                 'fooditem_set',
#                 queryset=FoodItem.objects.select_related('category').order_by('id'),
#                 to_attr='active_items'
#             )
#         )
#         food_items = FoodItem.objects.filter(
#             category__restaurant=restaurant
#         ).select_related('category').order_by('id')
#     else:
#         categories = Category.objects.filter(restaurant=restaurant).prefetch_related(
#             Prefetch(
#                 'fooditem_set',
#                 queryset=FoodItem.objects.filter(is_paused=False)
#                 .select_related('category')
#                 .order_by('id'),
#                 to_attr='active_items'
#             )
#         )
#         food_items = FoodItem.objects.filter(
#             category__restaurant=restaurant,
#             is_paused=False
#         ).select_related('category').order_by('id')

#     # -------- Safety normalization --------
#     if not is_owner:
#         for cat in categories:
#             ai = getattr(cat, 'active_items', [])
#             cat.active_items = [i for i in ai if not getattr(i, 'is_paused', False)]

#     return render(
#         request,
#         'restaurant/menu.html',
#         {
#             'restaurant': restaurant,
#             'table': table,
#             'categories': categories,
#             'food_items': food_items,
#         }
#     )

@require_POST
@login_required
def toggle_item_availability(request):
    """
    Toggle is_paused on a FoodItem. Return canonical state.
    JSON: { success: True, is_paused: bool, item_id: int }
    """
    item_id = request.POST.get('item_id') or request.POST.get('id')
    if not item_id:
        return HttpResponseBadRequest("Missing item_id")

    try:
        item = FoodItem.objects.select_related('category__restaurant').get(pk=int(item_id))
    except (FoodItem.DoesNotExist, ValueError):
        return HttpResponseBadRequest("Invalid item_id")

    # ownership check
    restaurant = getattr(request.user, 'restaurant', None)
    if not restaurant or item.category.restaurant_id != restaurant.id:
        return HttpResponseForbidden("Not allowed")

    # Determine new paused state (server authoritative)
    paused_val = request.POST.get('paused')
    if paused_val is None:
        item.is_paused = not item.is_paused
    else:
        item.is_paused = str(paused_val).lower() in ('1', 'true', 'yes')

    # Save canonical value to DB
    item.save(update_fields=['is_paused'])

    # Return canonical state back to client
    return JsonResponse({
        'success': True,
        'is_paused': bool(item.is_paused),
        'item_id': item.id
    })

# -----------------------
# QR code utilities
# -----------------------

# at top of views.py ensure you have request available imports and logger already defined
# logger = logging.getLogger(__name__)

@login_required
def create_table_qr_view(request):
    """
    List tables and mark which are scannable.
    If a table is scannable and QR is missing, generate it.
    """
    restaurant = get_object_or_404(Restaurant, owner=request.user)
    logger.info(f"[QR] Loading tables for restaurant {restaurant.id}")

    subscription = None
    allowed_table_ids = []
    allowed_table_limit = 0
    subscription_active = False

    try:
        subscription = restaurant.subscription
        if subscription and subscription.has_active_subscription():
            subscription_active = True
            allowed_table_limit = subscription.plan.table_limit if subscription.plan else 0
            allowed_table_ids = list(
                Table.objects.filter(restaurant=restaurant)
                .order_by("id")[:allowed_table_limit]
                .values_list("id", flat=True)
            )
    except Subscription.DoesNotExist:
        logger.warning(f"[QR] No subscription for restaurant {restaurant.id}")

    tables = Table.objects.filter(restaurant=restaurant).order_by("id")

    for table in tables:
        table.is_scannable = subscription_active and table.id in allowed_table_ids

        if table.is_scannable:
            try:
                if not table.qr_code or not default_storage.exists(table.qr_code.name):
                    logger.info(f"[QR] Generating QR for table {table.id}")
                    generate_qr_code(table, force=False)
            except Exception as e:
                logger.exception(f"[QR][ERROR] Failed QR for table {table.id}: {e}")

    context = {
        "restaurant": restaurant,
        "tables": tables,
        "subscription": subscription,
        "subscription_active": subscription_active,
        "allowed_table_limit": allowed_table_limit,
    }
    return render(request, "restaurant/create_table_qr.html", context)



def generate_qr_code(table, force=False):
    if not table.restaurant_id:
        raise ValueError("Table has no restaurant")

    # ALWAYS use POSIX path
    key = (
        f"qr_codes/"
        f"restaurant_{table.restaurant_id}/"
        f"table_{table.table_number}_qr.png"
    )

    key = key.replace("\\", "/")  # 🔴 CRITICAL

    logger.info(f"[QR] Using storage key: {key}")

    if not force:
        try:
            if default_storage.exists(key):
                table.qr_code.name = key
                table.save(update_fields=["qr_code"])
                return key
        except Exception as e:
            logger.warning(f"[QR] exists() failed: {e}")

    qr_url = f"https://www.zenqrmenu.com/menu/{table.restaurant_id}/{table.id}/"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    if force:
        try:
            if default_storage.exists(key):
                default_storage.delete(key)
        except Exception:
            pass

    saved_name = default_storage.save(key, ContentFile(buf.read()))

    # 🔴 Normalize AGAIN before saving to DB
    saved_name = saved_name.replace("\\", "/")

    table.qr_code.name = saved_name
    table.save(update_fields=["qr_code"])

    logger.info(f"[QR] QR saved at {saved_name}")
    return saved_name






def download_qr_code(request, table_id):
    """
    Download QR code image for a table using storage backend.
    Works for local, S3, and Cloudflare R2.
    """

    logger.debug(f"[QR] Download requested for table {table_id}")

    table = get_object_or_404(Table, id=table_id)

    if not table.qr_code:
        logger.warning(f"[QR][404] Table {table_id} has no QR assigned")
        raise Http404("QR Code not found.")

    key = table.qr_code.name.replace("\\", "/")


    try:
        file_obj = default_storage.open(key, "rb")
    except Exception as e:
        logger.error(f"[QR][404] Missing QR file {key}: {e}")
        raise Http404("QR Code file missing.")

    response = FileResponse(file_obj, content_type="image/png")
    response["Content-Disposition"] = (
        f'attachment; filename="table_{table.table_number}_qr.png"'
    )
    return response




# -----------------------
# Product / order flows
# -----------------------
def product_detail(request, restaurant_id, table_id, pk):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    fooditem = get_object_or_404(FoodItem, id=pk, category__restaurant=restaurant)

    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 1))
        order = Order.objects.create(table=table, restaurant=restaurant)
        OrderItem.objects.create(order=order, food_item=fooditem, quantity=quantity)
        return redirect("order_confirmation", order_id=order.id)

    return render(request, "restaurant/product_detail.html", {
        "restaurant": restaurant,
        "table": table,
        "fooditem": fooditem
    })


@require_POST
def add_to_order(request, restaurant_id, table_id, pk):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    item = get_object_or_404(FoodItem, id=pk, category__restaurant=restaurant)

    qty = int(request.POST.get('quantity', 1))
    order = Order.objects.create(table=table, restaurant=restaurant)
    oi = OrderItem.objects.create(order=order, food_item=item, quantity=qty)

    addon_ids = request.POST.getlist('addons')
    if addon_ids:
        addons = AddOn.objects.filter(id__in=addon_ids)
        oi.selected_addons.set(addons)

    return redirect('order_confirmation', order_id=order.id)


@require_http_methods(["GET", "POST"])
def product_detail_view(request, restaurant_id, table_id, pk):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    item = get_object_or_404(FoodItem, id=pk, category__restaurant=restaurant)

    if request.method == 'POST':
        order = Order.objects.create(table=table, restaurant=restaurant)
        qty = int(request.POST.get('quantity', 1))
        oi = OrderItem.objects.create(order=order, food_item=item, quantity=qty)
        addon_ids = request.POST.getlist('addons')
        if addon_ids:
            addons = AddOn.objects.filter(id__in=addon_ids)
            oi.selected_addons.set(addons)
        return redirect('order_confirmation', order_id=order.id)

    addons = item.addons.all()
    return render(request, 'restaurant/product_detail.html', {
        'restaurant': restaurant,
        'table': table,
        'item': item,
        'addons': addons,
    })


def product_detail_html(request, restaurant_id, table_id, pk):
    """
    Return rendered HTML fragment for product detail (suitable to inject into a modal).
    """
    try:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
        table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
        item = get_object_or_404(FoodItem, id=pk, category__restaurant=restaurant)
        addons = item.addons.all()

        html = render_to_string(
            'restaurant/product_detail_fragment.html',
            {'restaurant': restaurant, 'table': table, 'item': item, 'addons': addons},
            request=request
        )
        return HttpResponse(html)
    except Exception:
        logger.exception("product_detail_html failed for item %s (table %s, rest %s)", pk, table_id, restaurant_id)
        if settings.DEBUG:
            tb = traceback.format_exc()
            return HttpResponseServerError("<pre>Template/render error:\n\n{}</pre>".format(tb))
        else:
            return HttpResponseServerError("Could not render product details. Please try again.")


def product_json(request, restaurant_id, table_id, pk):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    item = get_object_or_404(FoodItem, id=pk, category__restaurant=restaurant)

    addons = [
        {"id": a.id, "name": a.name, "price": float(a.price)}
        for a in item.addons.all()
    ]

    data = {
        "id": item.id,
        "name": item.name,
        "description": item.description or "",
        "price": float(item.price),
        "image_url": item.image.url if item.image else None,
        "addons": addons
    }
    return JsonResponse(data)


# -----------------------
# Order helpers
# -----------------------
def _get_or_create_open_order(table, restaurant):
    """
    Return an existing open (is_completed=False) order for the table + restaurant,
    or create a new one.
    """
    order = Order.objects.filter(table=table, restaurant=restaurant, is_completed=False).first()
    if order:
        return order
    return Order.objects.create(table=table, restaurant=restaurant)


def _get_or_create_single_open_order(table, restaurant):
    """
    Return a single open Order for (table, restaurant). If multiple open orders
    exist, merge them into the oldest one and remove duplicates.
    """
    open_qs = Order.objects.filter(table=table, restaurant=restaurant, is_completed=False).order_by('created_at')
    if not open_qs.exists():
        return Order.objects.create(table=table, restaurant=restaurant, is_completed=False), True

    canonical = open_qs.first()
    duplicates = list(open_qs[1:])
    if duplicates:
        logger.warning("Merging %d duplicate open orders into order id=%s for table=%s",
                       len(duplicates), canonical.id, table.id)
        with transaction.atomic():
            for dup in duplicates:
                for oi in dup.order_items.all():
                    existing = None
                    dup_addon_ids = set(oi.selected_addons.values_list('id', flat=True))
                    for e in canonical.order_items.filter(food_item=oi.food_item):
                        e_addon_ids = set(e.selected_addons.values_list('id', flat=True))
                        if e_addon_ids == dup_addon_ids:
                            existing = e
                            break
                    if existing:
                        existing.quantity = (existing.quantity or 0) + (oi.quantity or 0)
                        existing.save()
                    else:
                        oi.order = canonical
                        oi.save()
                dup.delete()
    return canonical, False


@login_required
def completed_orders(request):
    """
    Show completed orders with search + date filters and daily totals.
    """
    try:
        restaurant = request.user.restaurant
    except Exception:
        return render(request, 'restaurant/completed_orders.html', {
            'orders': [],
            'totals_by_date': [],
            'query': '',
            'start_date': '',
            'end_date': '',
        })

    qs = Order.objects.filter(restaurant=restaurant, is_completed=True).prefetch_related(
        'order_items__food_item', 'order_items__selected_addons', 'table'
    ).order_by('-created_at')

    # Filters
    q = request.GET.get('q', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    if q:
        qs = qs.filter(
            Q(id__iexact=q) |
            Q(table__table_number__iexact=q) |
            Q(order_items__food_item__name__icontains=q)
        ).distinct()

    def parse_date(val):
        try:
            return datetime.datetime.strptime(val, "%Y-%m-%d").date()
        except Exception:
            return None

    sd = parse_date(start_date)
    ed = parse_date(end_date)
    if sd and ed and ed < sd:
        sd, ed = ed, sd

    if sd:
        qs = qs.filter(created_at__date__gte=sd)
    if ed:
        qs = qs.filter(created_at__date__lte=ed)

    # annotate base sums (optional DB-side help)
    price_expr = ExpressionWrapper(
        Sum(F('order_items__quantity') * F('order_items__food_item__price')),
        output_field=DecimalField(max_digits=12, decimal_places=2)
    )
    orders_with_totals = qs.annotate(order_base_sum=price_expr)

    orders_for_template = []
    totals_by_date = {}

    for o in orders_with_totals:
        total = Decimal('0.00')
        item_lines = []
        for it in o.order_items.all():
            item_price = Decimal(it.food_item.price or Decimal('0.00'))
            qty = int(it.quantity or 0)
            item_base = item_price * qty
            addons_price = sum((Decimal(a.price or Decimal('0.00')) for a in it.selected_addons.all())) * qty
            line_total = item_base + addons_price
            total += line_total

            item_lines.append({
                'id': it.id,
                'name': it.food_item.name,
                'quantity': qty,
                'addons': [{'id': a.id, 'name': a.name, 'price': a.price} for a in it.selected_addons.all()],
                'line_total': line_total,
            })

        # attach safe attributes (no leading underscore)
        o.item_lines = item_lines
        o.computed_total = total
        o.local_time = timezone.localtime(o.created_at)

        day = o.local_time.date()
        totals_by_date.setdefault(day, Decimal('0.00'))
        totals_by_date[day] += total

        orders_for_template.append(o)

    # sort totals_by_date descending
    totals_by_date_sorted = sorted(totals_by_date.items(), key=lambda x: x[0], reverse=True)

    context = {
        'orders': orders_for_template,
        'totals_by_date': totals_by_date_sorted,
        'query': q,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'restaurant/completed_orders.html', context)

# -----------------------
# AJAX endpoints
# -----------------------
@require_POST
def add_to_cart_ajax(request, restaurant_id, table_id, pk):
    """
    AJAX endpoint to add an item to the single open order for the table.
    Reuses existing open order if present; creates new open order otherwise.
    Returns JSON.
    """
    try:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
        # ensure table belongs to that restaurant
        table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
        item = get_object_or_404(FoodItem, id=pk, category__restaurant=restaurant)

        # parse quantity defensively
        try:
            qty = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            qty = 1
        if qty < 1:
            qty = 1

        # parse addons (supports addons[] and addons)
        raw_addons = request.POST.getlist('addons[]') or request.POST.getlist('addons') or []
        addon_ids = []
        for a in raw_addons:
            try:
                addon_ids.append(int(a))
            except (ValueError, TypeError):
                logger.warning("Ignored invalid addon id %r", a)
        addons_qs = AddOn.objects.filter(id__in=addon_ids) if addon_ids else AddOn.objects.none()

        # reuse single open order if exists
        order = Order.objects.filter(table=table, restaurant=table.restaurant, is_completed=False).order_by('created_at').first()
        if order:
            logger.info("Reusing open order id=%s for table=%s", order.id, table.id)
        else:
            order = Order.objects.create(table=table, restaurant=table.restaurant, is_completed=False)
            logger.info("Created new open order id=%s for table=%s", order.id, table.id)

        # <<-- ADDED DEBUG LOG: record creation/usage with user and timestamp
        logger.info(
            "Order created/used id=%s restaurant=%s table=%s user=%s created_at=%s",
            order.id,
            order.restaurant_id,
            order.table_id,
            request.user.id if request.user.is_authenticated else None,
            getattr(order, "created_at", None)
        )

        # add item
        oi = OrderItem.objects.create(order=order, food_item=item, quantity=qty)
        if addons_qs.exists():
            oi.selected_addons.set(addons_qs)

        # compute totals
        total_price = Decimal('0.00')
        total_count = 0
        for it in order.order_items.select_related('food_item').prefetch_related('selected_addons').all():
            base = (it.food_item.price or Decimal('0.00')) * (it.quantity or 0)
            addons_price = sum((a.price or Decimal('0.00')) for a in it.selected_addons.all()) * (it.quantity or 0)
            try:
                total_price += Decimal(base) + Decimal(addons_price)
            except (InvalidOperation, TypeError):
                total_price += Decimal(str(base)) + Decimal(str(addons_price))
            total_count += (it.quantity or 0)

        line_base = (item.price or Decimal('0.00')) * oi.quantity
        line_addons = sum((a.price or Decimal('0.00')) for a in oi.selected_addons.all()) * oi.quantity
        try:
            line_total = Decimal(line_base) + Decimal(line_addons)
        except (InvalidOperation, TypeError):
            line_total = Decimal(str(line_base)) + Decimal(str(line_addons))

        return JsonResponse({
            'success': True,
            'message': 'Added to cart',
            'order_id': order.id,
            'items_count': int(total_count),
            'total_price': float(total_price),
            'line_total': float(line_total),
        })
    except Exception as exc:
        tb = traceback.format_exc()
        logger.exception("add_to_cart_ajax error: %s", exc)
        if settings.DEBUG:
            return JsonResponse({'success': False, 'message': 'Server error', 'traceback': tb}, status=500)
        return JsonResponse({'success': False, 'message': 'Server error'}, status=500)



@require_POST
def delete_order_item_ajax(request, order_item_id):
    try:
        oi = get_object_or_404(OrderItem, id=order_item_id)
        order = oi.order
        oi.delete()

        total_price = Decimal('0.00')
        total_count = 0
        remaining_items = order.order_items.select_related('food_item').prefetch_related('selected_addons').all()
        for it in remaining_items:
            base = (it.food_item.price or Decimal('0.00')) * it.quantity
            addons_price = sum((a.price or Decimal('0.00')) for a in it.selected_addons.all()) * it.quantity
            total_price += Decimal(base) + Decimal(addons_price)
            total_count += it.quantity

        return JsonResponse({
            'success': True,
            'items_count': total_count,
            'total_price': float(total_price),
            'order_id': order.id,
        })
    except Exception as exc:
        logger.exception("delete_order_item_ajax failed: %s", exc)
        tb = traceback.format_exc()
        return JsonResponse({'success': False, 'message': 'Server error', 'traceback': tb}, status=500)


# @require_POST
# def confirm_order_ajax(request, order_id):
#     order = get_object_or_404(Order, id=order_id)
#     logger.info("confirm_order_ajax called by user=%s for order=%s", request.user.id if request.user.is_authenticated else None, order_id)
#     try:
#         order.is_completed = True
#         order.save()

#         total_price = 0.0
#         total_count = 0
#         for it in order.order_items.select_related('food_item').prefetch_related('selected_addons').all():
#             base = float(it.food_item.price or 0) * (it.quantity or 0)
#             addons_price = float(sum(a.price for a in it.selected_addons.all()) or 0) * (it.quantity or 0)
#             total_price += base + addons_price
#             total_count += (it.quantity or 0)

#         return JsonResponse({
#             'success': True,
#             'order_id': order.id,
#             'items_count': total_count,
#             'total_price': float(total_price),
#             'message': 'Order sent to kitchen'
#         })
#     except Exception as exc:
#         logger.exception("confirm_order_ajax failed: %s", exc)
#         tb = traceback.format_exc()
#         if settings.DEBUG:
#             return JsonResponse({'success': False, 'message': 'Server error', 'traceback': tb}, status=500)
#         return JsonResponse({'success': False, 'message': 'Server error'}, status=500)


# -----------------------
# Cart / placing / cancelling
# -----------------------
def cart_summary(request, restaurant_id, table_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)

    if not Order.objects.filter(table=table, restaurant=restaurant, is_completed=False).exists():
        return JsonResponse({'success': True, 'items_count': 0, 'total_price': 0.0})

    order, _ = _get_or_create_single_open_order(table, restaurant)

    total_price = Decimal('0.00')
    total_count = 0
    for it in order.order_items.select_related('food_item').prefetch_related('selected_addons').all():
        base = (it.food_item.price or Decimal('0.00')) * (it.quantity or 0)
        addons_price = sum((a.price or Decimal('0.00')) for a in it.selected_addons.all()) * it.quantity
        try:
            total_price += Decimal(base) + Decimal(addons_price)
        except (InvalidOperation, TypeError):
            total_price += Decimal(str(base)) + Decimal(str(addons_price))
        total_count += it.quantity

    return JsonResponse({
        'success': True,
        'items_count': int(total_count),
        'total_price': float(total_price),
        'order_id': order.id
    })


@require_POST
def place_cart_order(request, restaurant_id, table_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)

    order = Order.objects.filter(table=table, restaurant=restaurant, is_completed=False).first()
    if not order:
        messages.error(request, "Your cart is empty.")
        return redirect('menu_view', restaurant_id=restaurant.id, table_id=table.id)

    return redirect('order_confirmation', order_id=order.id)


@require_POST
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    restaurant_id = order.restaurant.id
    table_id = order.table.id
    order.delete()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({'success': True, 'order_id': order_id, 'redirect_url': reverse('menu_view', args=[restaurant_id, table_id])})

    messages.success(request, "Your order has been canceled successfully.")
    return redirect(reverse('menu_view', args=[restaurant_id, table_id]))


# -----------------------
# Order confirmation view
# -----------------------
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = order.order_items.prefetch_related("selected_addons", "food_item")

    total_price = 0
    for item in order_items:
        base_price = item.food_item.price * item.quantity
        addons_price = sum(addon.price for addon in item.selected_addons.all()) * item.quantity
        item.item_total = base_price + addons_price
        total_price += item.item_total

    if request.method == "POST":
        return redirect('menu_view', restaurant_id=order.restaurant.id, table_id=order.table.id)

    context = {
        'order': order,
        'order_items': order_items,
        'total_price': total_price
    }
    return render(request, 'restaurant/order_confirmation.html', context)


# -----------------------
# Kitchen views / polling
# -----------------------
# @login_required
# def kitchen_interface(request):
#     """
#     Render kitchen interface page with open orders.
#     Preserves previous behaviour:
#       - selects open orders (is_completed=False)
#       - prefetches order_items__food_item and selected_addons, table
#       - annotates total_price using expression
#       - populates order.local_time for template display
#     Adds defensive subscription lookups so templates can show/hide subscription-protected actions.
#     """
#     try:
#         restaurant = request.user.restaurant
#     except Restaurant.DoesNotExist:
#         # user has no restaurant; render page with empty orders for UX
#         return render(request, 'restaurant/kitchen.html', {
#             'orders': [],
#             'subscription': None,
#             'subscription_active': False,
#         })

#     total_expr = ExpressionWrapper(
#         Sum(F('order_items__quantity') * F('order_items__food_item__price')),
#         output_field=DecimalField(max_digits=12, decimal_places=2)
#     )

#     orders = (
#         Order.objects
#         .filter(restaurant=restaurant, is_completed=False)
#         .prefetch_related('order_items__food_item', 'order_items__selected_addons', 'table')
#         .annotate(total_price=total_expr)
#         .order_by('created_at')
#     )

#     # set a local_time attribute for template
#     for order in orders:
#         try:
#             order.local_time = timezone.localtime(order.created_at)
#         except Exception:
#             order.local_time = order.created_at

#     # Defensive subscription detection (so templates using these variables keep working).
#     subscription = None
#     subscription_active = False
#     try:
#         subscription = getattr(request.user, 'subscription', None) or getattr(restaurant, 'subscription', None)
#         if not subscription:
#             # try related managers if present
#             if hasattr(restaurant, 'subscriptions'):
#                 subscription = getattr(restaurant, 'subscriptions').order_by('-end_date').first()
#             elif hasattr(request.user, 'subscriptions'):
#                 subscription = getattr(request.user, 'subscriptions').order_by('-end_date').first()

#         if subscription:
#             end_date = getattr(subscription, 'end_date', None) or getattr(subscription, 'expires_at', None) or getattr(subscription, 'valid_until', None)
#             if end_date:
#                 subscription_active = end_date >= timezone.now()
#             else:
#                 subscription_active = bool(getattr(subscription, 'is_active', False) or getattr(subscription, 'active', False))
#     except Exception:
#         logger.debug("Subscription lookup failed: %s", traceback.format_exc())
#         subscription = subscription or None
#         subscription_active = False

#     return render(request, 'restaurant/kitchen.html', {
#         'orders': orders,
#         'subscription': subscription,
#         'subscription_active': subscription_active,
#     })


@login_required
def orders_json(request):
    """
    JSON endpoint polled by the kitchen UI.
    Returns open orders (is_completed=False) for the logged-in user's restaurant.
    Response format:
      { "success": True, "orders": [ { order_id, table_number, created_at, total, items: [...] }, ... ] }
    """
    try:
        restaurant = request.user.restaurant
    except Restaurant.DoesNotExist:
        return JsonResponse({'success': True, 'orders': []})

    orders_qs = (
        Order.objects
        .filter(restaurant=restaurant, is_completed=False)
        .prefetch_related('order_items__food_item', 'order_items__selected_addons', 'table')
        .order_by('created_at')
    )

    orders_data = []
    for order in orders_qs:
        total = Decimal('0.00')
        items = []
        for it in order.order_items.all():
            # compute addons and line totals
            addons = [{'id': a.id, 'name': a.name, 'price': float(a.price)} for a in it.selected_addons.all()]
            line_food = (it.food_item.price or Decimal('0.00')) * (it.quantity or 0)
            line_addons = sum((a.price or Decimal('0.00')) for a in it.selected_addons.all()) * (it.quantity or 0)
            try:
                line = float(line_food + line_addons)
            except Exception:
                # defensive fallback
                line = float(Decimal(str(line_food)) + Decimal(str(line_addons)))
            total += Decimal(str(line))
            items.append({
                'id': it.id,
                'name': it.food_item.name,
                'quantity': it.quantity,
                'addons': addons,
                'line_total': line,
            })

        orders_data.append({
            'order_id': order.id,
            'table_number': order.table.table_number if order.table else None,
            'created_at': (order.created_at.isoformat() if getattr(order, 'created_at', None) else None),
            'total': float(total),
            'items': items,
        })

    return JsonResponse({'success': True, 'orders': orders_data})

@login_required
def orders_json(request):
    """
    JSON endpoint polled by the kitchen UI.
    Returns open orders (is_completed=False) for the logged-in user's restaurant.
    Response format:
      { "success": True, "orders": [ { order_id, table_number, created_at, total, items: [...] }, ... ] }
    """
    try:
        restaurant = request.user.restaurant
    except Restaurant.DoesNotExist:
        return JsonResponse({'success': True, 'orders': []})

    orders_qs = (
        Order.objects
        .filter(restaurant=restaurant, is_completed=False)
        .prefetch_related('order_items__food_item', 'order_items__selected_addons', 'table')
        .order_by('created_at')
    )

    orders_data = []
    for order in orders_qs:
        total = Decimal('0.00')
        items = []
        for it in order.order_items.all():
            # compute addons and line totals
            addons = [{'id': a.id, 'name': a.name, 'price': float(a.price)} for a in it.selected_addons.all()]
            line_food = (it.food_item.price or Decimal('0.00')) * (it.quantity or 0)
            line_addons = sum((a.price or Decimal('0.00')) for a in it.selected_addons.all()) * (it.quantity or 0)
            try:
                line = float(line_food + line_addons)
            except Exception:
                # defensive fallback
                line = float(Decimal(str(line_food)) + Decimal(str(line_addons)))
            total += Decimal(str(line))
            items.append({
                'id': it.id,
                'name': it.food_item.name,
                'quantity': it.quantity,
                'addons': addons,
                'line_total': line,
            })

        orders_data.append({
            'order_id': order.id,
            'table_number': order.table.table_number if order.table else None,
            'created_at': (order.created_at.isoformat() if getattr(order, 'created_at', None) else None),
            'total': float(total),
            'items': items,
        })

    return JsonResponse({'success': True, 'orders': orders_data})


# @login_required
# def orders_json(request):
#     try:
#         restaurant = request.user.restaurant
#     except Restaurant.DoesNotExist:
#         return JsonResponse({'success': True, 'orders': []})

#     orders_qs = (
#         Order.objects
#         .filter(restaurant=restaurant, is_completed=False)
#         .prefetch_related('order_items__food_item', 'order_items__selected_addons', 'table')
#         .order_by('created_at')
#     )

#     orders_data = []
#     for order in orders_qs:
#         total = 0.0
#         items = []
#         for it in order.order_items.all():
#             addons = [{'id': a.id, 'name': a.name, 'price': float(a.price)} for a in it.selected_addons.all()]
#             line = float(it.food_item.price or 0) * it.quantity + sum(a['price'] for a in addons) * it.quantity
#             total += line
#             items.append({
#                 'id': it.id,
#                 'name': it.food_item.name,
#                 'quantity': it.quantity,
#                 'addons': addons,
#                 'line_total': line,
#             })
#         orders_data.append({
#             'order_id': order.id,
#             'table_number': order.table.table_number if order.table else None,
#             'created_at': order.created_at.isoformat(),
#             'total': total,
#             'items': items,
#         })

#     return JsonResponse({'success': True, 'orders': orders_data})


# -----------------------
# Utility: mark complete (simple view)
# -----------------------
# @login_required
# def complete_order(request, order_id):
#     order = get_object_or_404(Order, id=order_id, table__restaurant=request.user.restaurant)
#     order.is_completed = True
#     order.save()
#     return JsonResponse({'success': True, 'order_id': order.id})


# restaurant/views.py
from django.core.mail import send_mail
from django.http import JsonResponse
from django.conf import settings
import traceback

def test_email(request):
    try:
        result = send_mail(
            subject="Zen QR Menu - Render Email Test",
            message="If you received this, Brevo + Anymail works fine!",
            from_email=None,  # Uses DEFAULT_FROM_EMAIL
            recipient_list=["yourpersonalemail@gmail.com"],  # Replace with your inbox
            fail_silently=False,
        )
        return JsonResponse({
            "status": "success",
            "send_mail_result": result,
            "backend": settings.EMAIL_BACKEND,
            "from_email": settings.DEFAULT_FROM_EMAIL,
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error_type": str(type(e).__name__),
            "error_message": str(e),
            "traceback": traceback.format_exc(),
        }, status=500)


###################### RestaurantView Set #####################################



from rest_framework.viewsets import ModelViewSet
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from .models import Restaurant
from .serializers import RestaurantSerializer

class RestaurantViewSet(ModelViewSet):
    serializer_class = RestaurantSerializer
    permission_classes = [IsAuthenticated]

    # 🔥 REQUIRED FOR IMAGE UPLOAD
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        return Restaurant.objects.filter(owner=self.request.user)

    def get_serializer_context(self):
        return {'request': self.request}  # 🔥 REQUIRED
    


#################### AUTH APIS #####################################



######################### REGISTER API #########################

@api_view(['POST'])
def api_register(request):
    data = request.data

    username = data.get("username")
    email = data.get("email")
    password1 = data.get("password1")
    password2 = data.get("password2")

    errors = {}

    if not username:
        errors["username"] = ["This field is required."]
    if not email:
        errors["email"] = ["This field is required."]
    if password1 != password2:
        errors["password2"] = ["Passwords do not match."]

    if User.objects.filter(username=username).exists():
        errors["username"] = ["Username already exists."]

    if User.objects.filter(email=email).exists():
        errors["email"] = ["Email already exists."]

    if errors:
        return Response({"success": False, "errors": errors}, status=400)

    # ✅ Create user
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password1
    )

    # ✅ Create or get EmailAddress
    email_address, created = EmailAddress.objects.get_or_create(
        user=user,
        email=user.email,
        defaults={"primary": True, "verified": False}
    )

    # 🔥 Send verification email (NEW ALLAUTH METHOD)
    try:
        email_address.send_confirmation(request)
    except Exception as e:
        print("Email send error:", str(e))

    return Response({
        "success": True,
        "message": "Account created. Please verify your email.",
        "email": user.email
    })


######################### LOGIN API #########################

@api_view(['POST'])
def api_login(request):
    username_or_email = request.data.get("username")
    password = request.data.get("password")

    if not username_or_email or not password:
        return Response({"error": "Missing credentials"}, status=400)

    # 🔐 Try username login
    user = authenticate(username=username_or_email, password=password)

    # 🔁 Fallback to email login
    if user is None:
        try:
            user_obj = User.objects.get(email=username_or_email)
            if user_obj.check_password(password):
                user = user_obj
        except User.DoesNotExist:
            return Response({"error": "Invalid credentials"}, status=400)

    if not user:
        return Response({"error": "Invalid credentials"}, status=400)

    # 🚨 Email verification check
    email_obj = EmailAddress.objects.filter(user=user, email=user.email).first()

    if email_obj:
        if not email_obj.verified:
            try:
                # 🔥 resend verification
                email_obj.send_confirmation(request)
            except Exception as e:
                print("Email send error:", str(e))

            return Response({
                "error": "Email not verified. Verification email sent.",
                "email": user.email
            }, status=403)
    else:
        # if missing, create and send
        email_obj = EmailAddress.objects.create(
            user=user,
            email=user.email,
            verified=False,
            primary=True
        )

        try:
            email_obj.send_confirmation(request)
        except Exception as e:
            print("Email send error:", str(e))

        return Response({
            "error": "Email not verified. Verification email sent.",
            "email": user.email
        }, status=403)

    # ✅ Generate JWT
    refresh = RefreshToken.for_user(user)

    return Response({
        "message": "Login successful",
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    })


######################### LOGOUT API #########################

@api_view(['POST'])
def api_logout(request):
    return Response({
        "success": True,
        "message": "Logged out (delete token on frontend)"
    })


######################### USER API #########################

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_user(request):
    return Response({
        "success": True,
        "user": {
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email
        }
    })


######################### DASHBOARD API #########################

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_api(request):
    return Response({
        "message": f"Welcome {request.user.username}"
    })


############ CATEGORY APIs ################


def get_user_restaurant(user):
    return Restaurant.objects.filter(owner=user).first()

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def categories_api(request):

    restaurant = get_user_restaurant(request.user)
    if not restaurant:
        return JsonResponse({"error": "Restaurant not found"}, status=404)

    if request.method == 'GET':
        cats = Category.objects.filter(restaurant=restaurant)
        return JsonResponse(
            [{"id": c.id, "name": c.name} for c in cats],
            safe=False
        )

    if request.method == 'POST':
        name = request.data.get("name")

        if not name:
            return JsonResponse({"error": "Name required"}, status=400)

        name = name.strip().title()

        category, _ = Category.objects.get_or_create(
            name=name,
            restaurant=restaurant
        )

        return JsonResponse({"id": category.id, "name": category.name}, status=201)
    


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def category_detail_api(request, id):

    try:
        category = Category.objects.get(id=id, restaurant__owner=request.user)
    except Category.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    if request.method == 'PATCH':
        category.name = request.data.get("name", category.name)
        category.save()

        return JsonResponse({"id": category.id, "name": category.name})

    if request.method == 'DELETE':
        category.delete()
        return JsonResponse({"success": True})
    





@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def menu_items_api(request):

    # ✅ Get restaurant safely
    try:
        restaurant = Restaurant.objects.get(owner=request.user)
    except Restaurant.DoesNotExist:
        return JsonResponse({"error": "Restaurant not found"}, status=404)

    # ✅ FIX: pass restaurant (NOT user)
    is_valid, result = check_subscription_access(restaurant)

    if not is_valid:
        return JsonResponse({
            "success": False,
            "error": result,
            "debug": {
                "user": request.user.id,
                "restaurant": restaurant.id,
            }
        }, status=403)
    
        # return JsonResponse({"success": False, "error": result}, status=403)

    plan = result

    # ========================
    # ✅ GET MENU ITEMS
    # ========================
    if request.method == 'GET':
        items = FoodItem.objects.filter(restaurant=restaurant)

        data = []
        for i in items:
            data.append({
                "id": i.id,
                "name": i.name,
                "price": float(i.price),
                "description": i.description,
                "category": i.category.id if i.category else None,
                "is_available": not i.is_paused,
                "image": i.image.url if i.image else None
            })

        return JsonResponse(data, safe=False)

    # ========================
    # ✅ CREATE MENU ITEM
    # ========================
    if request.method == 'POST':

        # ❌ REMOVE menu_item_limit restriction for free plan
        # (free = unlimited items)

        name = request.data.get("name", "").strip().title()
        price = request.data.get("price")
        description = request.data.get("description", "")
        category_id = request.data.get("category")
        image = request.FILES.get("image")

        if not name or not price:
            return JsonResponse({
                "error": "Name and price are required"
            }, status=400)

        category = Category.objects.filter(
            id=category_id,
            restaurant=restaurant
        ).first()

        if not category:
            return JsonResponse({"error": "Invalid category"}, status=400)

        try:
            item = FoodItem.objects.create(
                name=name,
                price=price,
                description=description,
                restaurant=restaurant,
                category=category,
                image=image
            )
        except Exception as e:
            return JsonResponse({
                "error": "Failed to create item",
                "details": str(e)
            }, status=500)

        print("USER:", request.user.id)
        print("RESTAURANT:", restaurant.id)


        return JsonResponse({
            "success": True,
            "id": item.id
        }, status=201)
    

@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def menu_item_detail_api(request, id):

    try:
        item = FoodItem.objects.get(id=id, restaurant__owner=request.user)
    except FoodItem.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    if request.method == 'PATCH':
        item.name = request.data.get("name", item.name)
        item.price = request.data.get("price", item.price)
        item.description = request.data.get("description", item.description)
        item.category_id = request.data.get("category", item.category_id)

        if "is_available" in request.data:
            item.is_paused = not request.data.get("is_available")

        if request.FILES.get("image"):
            item.image = request.FILES.get("image")

        item.save()

        return JsonResponse({
            "id": item.id,
            "name": item.name,
            "price": float(item.price),
            "description": item.description,
            "category": item.category.id if item.category else None,
            "is_available": not item.is_paused,
            "image": item.image.url if item.image else None
        })

    if request.method == 'DELETE':
        item.delete()
        return JsonResponse({"success": True})
    
################ KITCHEN STATUS ON MENU ########################



@api_view(['GET'])
@permission_classes([AllowAny])
def public_order_detail(request, pk):
    try:
        order = Order.objects.get(pk=pk)   # ✅ FIXED HERE
    except Order.DoesNotExist:
        return Response({'detail': 'Not found'}, status=404)

    return Response({
        "id": order.id,
        "status": order.status,
        "table": order.table.id if order.table else None,
        "total": float(order.total_price_cached) if hasattr(order, 'total_price_cached') else 0,
    })


################### TABLE API ################################
    



from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from restaurant.models import Table
from subscription.utils import check_subscription_access
import qrcode
from io import BytesIO
from django.core.files import File


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def create_table_api(request):

    # ✅ Get restaurant
    restaurant = get_user_restaurant(request.user)
    if not restaurant:
        return JsonResponse({"error": "Restaurant not found"}, status=404)

    # ========================
    # ✅ GET TABLES
    # ========================
    if request.method == 'GET':
        tables = Table.objects.filter(restaurant=restaurant).order_by('table_number')

        data = [{
            "id": t.id,
            "table_number": t.table_number,
            "qr_code": t.qr_code.url if t.qr_code else None
        } for t in tables]

        return JsonResponse(data, safe=False)

    # ========================
    # ✅ CREATE TABLE
    # ========================
    if request.method == 'POST':

        # ✅ FIX: pass restaurant
        is_valid, plan = check_subscription_access(restaurant)

        if not is_valid:
            return JsonResponse({
                "success": False,
                "error": plan,
                "debug": {
                    "user": request.user.id,
                    "restaurant": restaurant.id,
                }
            }, status=403)
        
            # return JsonResponse({"success": False, "error": result}, status=403)

        # ✅ Get current count
        table_count = Table.objects.filter(restaurant=restaurant).count()

        # ✅ Apply limit ONLY if exists
        if plan.table_limit is not None:
            if table_count >= plan.table_limit:
                return JsonResponse({
                    "success": False,
                    "error": f"Table limit reached ({plan.table_limit})"
                }, status=403)

        # ✅ Validate input
        table_number = request.data.get("table_number")

        if not table_number:
            return JsonResponse({"error": "table_number is required"}, status=400)

        # Optional: prevent duplicates
        if Table.objects.filter(restaurant=restaurant, table_number=table_number).exists():
            return JsonResponse({
                "error": "Table number already exists"
            }, status=400)

        # ✅ Create table
        table = Table.objects.create(
            restaurant=restaurant,
            table_number=table_number
        )

        # ✅ Generate QR
        qr_url = request.build_absolute_uri(f"/menu/table/{table.id}/")

        qr = qrcode.make(qr_url)

        buffer = BytesIO()
        qr.save(buffer, format="PNG")

        file_name = f"table_{table.id}.png"
        table.qr_code.save(file_name, File(buffer), save=True)

        return JsonResponse({
            "success": True,
            "id": table.id,
            "table_number": table.table_number,
            "qr_code": table.qr_code.url,
            "qr_url": qr_url
        }, status=201)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_table_api(request, table_id):

    try:
        restaurant = Restaurant.objects.get(owner=request.user)
    except Restaurant.DoesNotExist:
        return JsonResponse({"error": "Restaurant not found"}, status=404)

    try:
        table = Table.objects.get(id=table_id, restaurant=restaurant)
    except Table.DoesNotExist:
        return JsonResponse({"error": "Table not found"}, status=404)

    # ✅ Delete QR image file (important cleanup)
    if table.qr_code:
        table.qr_code.delete(save=False)

    table.delete()

    return JsonResponse({"success": True})


########## Public Menu ###################



@cache_page(60 * 2)  # cache for 2 minutes (fast QR loading)
@api_view(["GET"])
@permission_classes([AllowAny])
def public_menu(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)

    categories = Category.objects.filter(restaurant=restaurant)
    items = FoodItem.objects.filter(
        restaurant=restaurant,
        is_paused=False
    ).select_related("category").prefetch_related("addons")

    # ✅ Categories
    categories_data = [
        {
            "id": c.id,
            "name": c.name,
        }
        for c in categories
    ]

    # ✅ Items
    items_data = [
        {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "price": float(item.price),
            "image": item.image.url if item.image else None,
            "category": item.category.id,
            "addons": [
                {
                    "id": a.id,
                    "name": a.name,
                    "price": float(a.price),
                }
                for a in item.addons.all()
            ],
        }
        for item in items
    ]

    return Response({
        "restaurant": {
            "id": restaurant.id,
            "name": restaurant.name,
            "address": restaurant.address,
            "logo": restaurant.logo.url if restaurant.logo else None,
            "cover_image": restaurant.cover_image.url if restaurant.cover_image else None,  # ✅ matches your fix
        },
        "categories": categories_data,
        "items": items_data,
    })


############ Restaurant Profile #########################


@api_view(['GET', 'POST', 'PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def restaurant_profile(request):

    try:

        restaurant = Restaurant.objects.filter(
            owner=request.user
        ).first()

        # =====================================================
        # GET RESTAURANT
        # =====================================================

        if request.method == 'GET':

            if not restaurant:

                return JsonResponse({
                    "success": True,
                    "restaurant": None,
                    "subscription": None
                })

            subscription = (
                Subscription.objects
                .filter(
                    restaurant=restaurant,
                    is_active=True
                )
                .select_related("plan")
                .first()
            )

            plan = (
                subscription.plan
                if subscription and subscription.plan
                else None
            )

            # =====================================================
            # IMAGE URLS
            # =====================================================

            logo_url = None
            cover_image_url = None

            if restaurant.logo:

                try:
                    logo_url = request.build_absolute_uri(
                        restaurant.logo.url
                    )
                except Exception:
                    logo_url = None

            if restaurant.cover_image:

                try:
                    cover_image_url = request.build_absolute_uri(
                        restaurant.cover_image.url
                    )
                except Exception:
                    cover_image_url = None

            return JsonResponse({

                "success": True,

                "restaurant": {

                    "id": restaurant.id,

                    "name": restaurant.name,

                    "cuisine": restaurant.cuisine_type,

                    "address": restaurant.address,

                    "phone": restaurant.phone,

                    "about": restaurant.about,

                    # IMPORTANT
                    "logo": logo_url,

                    "logo_url": logo_url,

                    "cover_image": cover_image_url,

                    "cover_image_url": cover_image_url,
                },

                "subscription": {

                    "plan": (
                        plan.name
                        if plan
                        else None
                    ),

                    "is_active": (
                        subscription.is_active
                        if subscription
                        else False
                    ),

                    "table_limit": (
                        getattr(plan, "table_limit", None)
                        if plan
                        else None
                    ),
                }
            })

        # =====================================================
        # CREATE RESTAURANT
        # =====================================================

        elif request.method == 'POST':

            if restaurant:

                return JsonResponse({
                    "success": False,
                    "error": "Restaurant already exists"
                }, status=400)

            restaurant = Restaurant.objects.create(
                owner=request.user,
                name=request.data.get("name", ""),
                cuisine_type=request.data.get("cuisine", ""),
                address=request.data.get("address", ""),
                phone=request.data.get("phone", ""),
                about=request.data.get("about", ""),
            )

            # =====================================================
            # IMAGE UPLOADS
            # =====================================================

            if request.FILES.get("logo"):
                restaurant.logo = request.FILES.get("logo")

            if request.FILES.get("cover_image"):
                restaurant.cover_image = request.FILES.get(
                    "cover_image"
                )

            restaurant.save()

            logo_url = (
                request.build_absolute_uri(
                    restaurant.logo.url
                )
                if restaurant.logo
                else None
            )

            cover_image_url = (
                request.build_absolute_uri(
                    restaurant.cover_image.url
                )
                if restaurant.cover_image
                else None
            )

            return JsonResponse({

                "success": True,

                "restaurant": {

                    "id": restaurant.id,

                    "name": restaurant.name,

                    "cuisine": restaurant.cuisine_type,

                    "address": restaurant.address,

                    "phone": restaurant.phone,

                    "about": restaurant.about,

                    "logo": logo_url,

                    "logo_url": logo_url,

                    "cover_image": cover_image_url,

                    "cover_image_url": cover_image_url,
                }
            })

        # =====================================================
        # UPDATE RESTAURANT
        # =====================================================

        elif request.method == 'PATCH':

            # =====================================================
            # AUTO CREATE FOR FRESH USERS
            # IMPORTANT FIX
            # =====================================================

            if not restaurant:

                print(
                    "NO RESTAURANT FOUND -> AUTO CREATING"
                )

                restaurant = Restaurant.objects.create(
                    owner=request.user,
                    name=request.data.get("name", ""),
                    cuisine_type=request.data.get(
                        "cuisine",
                        ""
                    ),
                    address=request.data.get(
                        "address",
                        ""
                    ),
                    phone=request.data.get(
                        "phone",
                        ""
                    ),
                    about=request.data.get(
                        "about",
                        ""
                    ),
                )

                # HANDLE IMAGES
                if request.FILES.get("logo"):

                    restaurant.logo = request.FILES.get(
                        "logo"
                    )

                if request.FILES.get("cover_image"):

                    restaurant.cover_image = request.FILES.get(
                        "cover_image"
                    )

                restaurant.save()

            else:

                # =====================================================
                # DEBUG FILES
                # =====================================================

                print("FILES:", request.FILES)

                # =====================================================
                # TEXT FIELDS
                # =====================================================

                if "name" in request.data:
                    restaurant.name = request.data.get(
                        "name"
                    )

                if "cuisine" in request.data:
                    restaurant.cuisine_type = request.data.get(
                        "cuisine"
                    )

                if "address" in request.data:
                    restaurant.address = request.data.get(
                        "address"
                    )

                if "phone" in request.data:
                    restaurant.phone = request.data.get(
                        "phone"
                    )

                if "about" in request.data:
                    restaurant.about = request.data.get(
                        "about"
                    )

                # =====================================================
                # IMAGE FILES
                # =====================================================

                if request.FILES.get("logo"):

                    restaurant.logo = request.FILES.get(
                        "logo"
                    )

                    print(
                        "NEW LOGO:",
                        restaurant.logo
                    )

                if request.FILES.get("cover_image"):

                    restaurant.cover_image = request.FILES.get(
                        "cover_image"
                    )

                    print(
                        "NEW COVER:",
                        restaurant.cover_image
                    )

                restaurant.save()

            # =====================================================
            # REFRESH
            # =====================================================

            restaurant.refresh_from_db()

            # =====================================================
            # IMAGE URLS
            # =====================================================

            logo_url = None
            cover_image_url = None

            if restaurant.logo:

                try:
                    logo_url = request.build_absolute_uri(
                        restaurant.logo.url
                    )
                except Exception:
                    logo_url = None

            if restaurant.cover_image:

                try:
                    cover_image_url = request.build_absolute_uri(
                        restaurant.cover_image.url
                    )
                except Exception:
                    cover_image_url = None

            return JsonResponse({

                "success": True,

                "message": "Restaurant saved successfully",

                "restaurant": {

                    "id": restaurant.id,

                    "name": restaurant.name,

                    "cuisine": restaurant.cuisine_type,

                    "address": restaurant.address,

                    "phone": restaurant.phone,

                    "about": restaurant.about,

                    "logo": logo_url,

                    "logo_url": logo_url,

                    "cover_image": cover_image_url,

                    "cover_image_url": cover_image_url,
                }
            })

    except Exception as e:

        print("RESTAURANT PROFILE ERROR:", str(e))

        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


##################### Order APIs ##################################



class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]  # QR public order
        return [IsAuthenticated()]  # dashboard

    def get_queryset(self):
        user = self.request.user

        # dashboard → only owner's restaurant orders
        if user.is_authenticated:
            return Order.objects.filter(restaurant__owner=user).order_by('-created_at')

        return super().get_queryset()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
    

###################### Menu View By Table ###############################



def menu_view_by_table(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    restaurant = table.restaurant

    return render(request, 'menu.html', {
        'restaurant_id': restaurant.id,
        'table_id': table.id
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def public_menu_by_table(request, table_id):

    table = get_object_or_404(Table, id=table_id)
    restaurant = table.restaurant

    categories = Category.objects.filter(restaurant=restaurant)

    items = FoodItem.objects.filter(
        restaurant=restaurant,
        is_paused=False
    ).select_related("category").prefetch_related("addons")

    categories_data = [
        {
            "id": c.id,
            "name": c.name,
        }
        for c in categories
    ]

    items_data = [
        {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "price": float(item.price),
            "image": item.image.url if item.image else None,
            "category": item.category.id,
            "addons": [
                {
                    "id": a.id,
                    "name": a.name,
                    "price": float(a.price),
                }
                for a in item.addons.all()
            ],
        }
        for item in items
    ]

    return Response({
            "restaurant": {
                "id": restaurant.id,
                "name": restaurant.name,
                "logo": request.build_absolute_uri(restaurant.logo.url) if restaurant.logo else None,
                "cover_image": request.build_absolute_uri(restaurant.cover_image.url) if restaurant.cover_image else None,
                "address": restaurant.address,
            },
            "table": {
                "id": table.id,
                "table_number": table.table_number
            },
            "categories": categories_data,
            "items": items_data,
        })


######################### EMAIL UPDATE/VERIFICATION ########################

############################################################################




@api_view(['POST'])
def resend_verification(request):
    email = request.data.get("email")

    if not email:
        return Response({"error": "Email required"}, status=400)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    email_obj = EmailAddress.objects.filter(user=user, email=email).first()

    if email_obj and email_obj.verified:
        return Response({"message": "Email already verified"}, status=400)

    # create if missing
    if not email_obj:
        EmailAddress.objects.create(
            user=user,
            email=email,
            verified=False,
            primary=True
        )

    # send email
    get_adapter(request).send_confirmation_mail(request, user, signup=False)

    return Response({"message": "Verification email sent"})



@api_view(['POST'])
def password_reset(request):
    email = request.data.get("email")

    if not email:
        return Response({"error": "Email required"}, status=400)

    form = ResetPasswordForm(data={"email": email})

    if form.is_valid():
        form.save(request=request)
        return Response({"message": "Password reset email sent"})

    return Response({"error": "Invalid email"}, status=400)




@api_view(['POST'])
def password_reset_confirm(request):
    uid = request.data.get("uid")
    token = request.data.get("token")
    password1 = request.data.get("new_password1")
    password2 = request.data.get("new_password2")

    if password1 != password2:
        return Response({"error": "Passwords do not match"}, status=400)

    try:
        user_id = urlsafe_base64_decode(uid).decode()
        user = User.objects.get(pk=user_id)
    except Exception:
        return Response({"error": "Invalid UID"}, status=400)

    if not default_token_generator.check_token(user, token):
        return Response({"error": "Invalid token"}, status=400)

    user.set_password(password1)
    user.save()

    return Response({"message": "Password reset successful"})





@api_view(['POST'])
def google_login(request):
    id_token_from_frontend = request.data.get("id_token")

    if not id_token_from_frontend:
        return Response({"error": "No token"}, status=400)

    try:
        idinfo = id_token.verify_oauth2_token(
            id_token_from_frontend,
            google_requests.Request(),
            "886773285585-fg35vj7ot1884qvkp64q9l7n8gst3tfn.apps.googleusercontent.com"
        )

        email = idinfo['email']

        users = User.objects.filter(email=email)

        if users.exists():
            user = users.first()   # ✅ pick first user
        else:
            user = User.objects.create(
                email=email,
                username=email.split("@")[0]
            )

        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })

    except Exception as e:
        return Response({"error": str(e)}, status=400)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_detail_api(request):
    return Response({
        "user": {
            "id": request.user.id,
            "email": request.user.email,
            "username": request.user.username,
        }
    })


#======================= specific commit revert==========================