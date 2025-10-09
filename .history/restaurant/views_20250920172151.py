# restaurant/views.py
import json
import logging
import os
import traceback
from decimal import Decimal, InvalidOperation

from io import BytesIO
import qrcode

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseServerError,
    JsonResponse,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout
from django.contrib import messages
from django.views.generic import CreateView, UpdateView, DeleteView

from .forms import FoodItemForm
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

logger = logging.getLogger(__name__)


# -----------------------
# Authentication helpers
# -----------------------
def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'restaurant/signup.html', {'form': form})


class CustomLogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('login')

    def get(self, request):
        logout(request)
        return redirect('login')


# -----------------------
# Restaurant / table CRUD
# -----------------------
def create_restaurant(request):
    if request.method == 'POST':
        Restaurant.objects.create(
            owner=request.user,
            name=request.POST.get('name'),
            address=request.POST.get('address'),
            about=request.POST.get('about', ''),
            cover_image=request.FILES.get('cover_image'),
        )
        return redirect('dashboard')
    return render(request, 'restaurant/create_restaurant.html')


class TableCreateView(LoginRequiredMixin, CreateView):
    model = Table
    fields = ['table_number']
    template_name = 'restaurant/table_form.html'
    success_url = reverse_lazy('create_table_qr')

    def form_valid(self, form):
        form.instance.restaurant = self.request.user.restaurant
        response = super().form_valid(form)
        try:
            generate_qr_code(self.object)
        except Exception:
            logger.exception("Failed to generate QR for table %s", getattr(self.object, 'id', None))
        return response


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    fields = ['name']
    template_name = 'restaurant/category_form.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        form.instance.restaurant = self.request.user.restaurant
        return super().form_valid(form)


class FoodItemCreateView(LoginRequiredMixin, CreateView):
    model = FoodItem
    form_class = FoodItemForm
    template_name = 'restaurant/fooditem_form.html'
    success_url = reverse_lazy('dashboard')

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
        return reverse_lazy('dashboard')

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
        return reverse_lazy('dashboard')

    def delete(self, request, *args, **kwargs):
        food_item = self.get_object()
        if food_item.category.restaurant != self.request.user.restaurant:
            messages.error(self.request, "Unauthorized action.")
            return redirect('dashboard')
        return super().delete(request, *args, **kwargs)


# -----------------------
# Dashboard / menu
# -----------------------
@login_required
def dashboard(request):
    try:
        restaurant = request.user.restaurant
    except Restaurant.DoesNotExist:
        return render(request, 'restaurant/create_restaurant.html')

    has_subscription = False
    try:
        subscription = restaurant.subscription
        if subscription and subscription.has_active_subscription():
            has_subscription = True
    except Subscription.DoesNotExist:
        has_subscription = False

    categories = Category.objects.filter(restaurant=restaurant)
    tables = Table.objects.filter(restaurant=restaurant)

    context = {
        'restaurant': restaurant,
        'tables': tables,
        'categories': categories,
        'has_subscription': has_subscription,
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


def menu_view(request, restaurant_id, table_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)

    categories = Category.objects.filter(restaurant=restaurant)
    food_items = FoodItem.objects.filter(category__restaurant=restaurant)

    context = {
        'restaurant': restaurant,
        'table': table,
        'categories': categories,
        'food_items': food_items
    }
    return render(request, 'restaurant/menu.html', context)


# -----------------------
# QR code utilities
# -----------------------


def generate_qr_code(table):
    """Generate and save a unique QR code for the given Table instance."""
    if not table.qr_code:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        if not table.restaurant or not table.restaurant.id:
            raise ValueError("Table must be associated with a valid restaurant.")

        local_url = f"http://127.0.0.1:8000/menu/{table.restaurant.id}/{table.id}/"
        qr.add_data(local_url)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')

        qr_folder = os.path.join(settings.MEDIA_ROOT, 'qr_codes', f'restaurant_{table.restaurant.id}')
        os.makedirs(qr_folder, exist_ok=True)

        file_name = f'table_{table.table_number}_qr.png'
        file_path = os.path.join(qr_folder, file_name)
        img.save(file_path)

        table.qr_code.name = os.path.join('qr_codes', f'restaurant_{table.restaurant.id}', file_name)
        table.save()


def download_qr_code(request, table_id):
    try:
        table = Table.objects.get(id=table_id)
        if not table.qr_code:
            raise Http404("QR Code not found.")
        qr_path = os.path.join(settings.MEDIA_ROOT, table.qr_code.name)
        if not os.path.exists(qr_path):
            raise Http404("QR Code file missing.")
        response = FileResponse(open(qr_path, "rb"), content_type="image/png")
        response["Content-Disposition"] = f'attachment; filename="table_{table.table_number}_qr.png"'
        return response
    except Table.DoesNotExist:
        raise Http404("Table not found.")


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


@require_POST
def confirm_order_ajax(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    logger.info("confirm_order_ajax called by user=%s for order=%s", request.user.id if request.user.is_authenticated else None, order_id)
    try:
        order.is_completed = True
        order.save()

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
            'message': 'Order sent to kitchen'
        })
    except Exception as exc:
        logger.exception("confirm_order_ajax failed: %s", exc)
        tb = traceback.format_exc()
        if settings.DEBUG:
            return JsonResponse({'success': False, 'message': 'Server error', 'traceback': tb}, status=500)
        return JsonResponse({'success': False, 'message': 'Server error'}, status=500)


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
@login_required
def kitchen_interface(request):
    try:
        restaurant = request.user.restaurant
    except Restaurant.DoesNotExist:
        return render(request, 'restaurant/kitchen.html', {'orders': []})

    total_expr = ExpressionWrapper(
        Sum(F('order_items__quantity') * F('order_items__food_item__price')),
        output_field=DecimalField(max_digits=12, decimal_places=2)
    )

    orders = (
        Order.objects
        .filter(restaurant=restaurant, is_completed=False)
        .prefetch_related('order_items__food_item', 'order_items__selected_addons', 'table')
        .annotate(total_price=total_expr)
        .order_by('created_at')
    )

    for order in orders:
        order.local_time = timezone.localtime(order.created_at)

    return render(request, 'restaurant/kitchen.html', {'orders': orders})


@login_required
def orders_json(request):
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
        total = 0.0
        items = []
        for it in order.order_items.all():
            addons = [{'id': a.id, 'name': a.name, 'price': float(a.price)} for a in it.selected_addons.all()]
            line = float(it.food_item.price or 0) * it.quantity + sum(a['price'] for a in addons) * it.quantity
            total += line
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
            'created_at': order.created_at.isoformat(),
            'total': total,
            'items': items,
        })

    return JsonResponse({'success': True, 'orders': orders_data})


# -----------------------
# Utility: mark complete (simple view)
# -----------------------
@login_required
def complete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, table__restaurant=request.user.restaurant)
    order.is_completed = True
    order.save()
    return JsonResponse({'success': True, 'order_id': order.id})
