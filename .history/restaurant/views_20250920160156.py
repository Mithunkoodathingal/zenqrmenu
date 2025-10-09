# restaurant/views.py
import os, json, traceback, logging, qrcode
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.urls import reverse, reverse_lazy
from django.shortcuts import render, get_object_or_404, redirect
from django.http import (
    JsonResponse, HttpResponse, HttpResponseServerError,
    Http404, FileResponse
)
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView, UpdateView, DeleteView
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm
from django.views import View
from django.db import transaction
from django.db.models import Sum, F, DecimalField, ExpressionWrapper

from .models import Restaurant, Table, Category, FoodItem, Order, OrderItem, AddOn
from .forms import FoodItemForm
from subscription.models import Subscription

logger = logging.getLogger(__name__)


# ---------------------------
# Helpers
# ---------------------------
def _safe_decimal(v):
    if isinstance(v, Decimal):
        return v
    try:
        return Decimal(v)
    except (InvalidOperation, TypeError, ValueError):
        try:
            return Decimal(str(v))
        except Exception:
            return Decimal('0.00')


def _get_or_create_single_open_order(table, restaurant):
    """Ensure only one open order exists for (table, restaurant)."""
    open_qs = Order.objects.filter(table=table, restaurant=restaurant, is_completed=False).order_by('created_at')
    if not open_qs.exists():
        return Order.objects.create(table=table, restaurant=restaurant, is_completed=False), True

    canonical = open_qs.first()
    duplicates = list(open_qs[1:])
    if duplicates:
        with transaction.atomic():
            for dup in duplicates:
                for oi in list(dup.order_items.all()):
                    dup_addons = set(oi.selected_addons.values_list('id', flat=True))
                    existing = None
                    for e in canonical.order_items.filter(food_item=oi.food_item):
                        e_addons = set(e.selected_addons.values_list('id', flat=True))
                        if e_addons == dup_addons:
                            existing = e
                            break
                    if existing:
                        existing.quantity += oi.quantity
                        existing.save()
                        oi.delete()
                    else:
                        oi.order = canonical
                        oi.save()
                dup.delete()
    return canonical, False


# ---------------------------
# Auth & Restaurant setup
# ---------------------------
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


def create_restaurant(request):
    if request.method == 'POST':
        Restaurant.objects.create(
            owner=request.user,
            name=request.POST['name'],
            address=request.POST['address'],
            about=request.POST.get('about', ''),
            cover_image=request.FILES.get('cover_image')
        )
        return redirect('dashboard')
    return render(request, 'restaurant/create_restaurant.html')


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
        pass

    categories = Category.objects.filter(restaurant=restaurant)
    tables = Table.objects.filter(restaurant=restaurant)

    return render(request, 'restaurant/manage_menu.html', {
        'restaurant': restaurant,
        'tables': tables,
        'categories': categories,
        'has_subscription': has_subscription,
    })


# ---------------------------
# Table & Category CRUD
# ---------------------------
class TableCreateView(CreateView):
    model = Table
    fields = ['table_number']
    template_name = 'restaurant/table_form.html'
    success_url = reverse_lazy('create_table_qr')

    def form_valid(self, form):
        form.instance.restaurant = self.request.user.restaurant
        response = super().form_valid(form)
        generate_qr_code(self.object)
        return response


class CategoryCreateView(CreateView):
    model = Category
    fields = ['name']
    template_name = 'restaurant/category_form.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        form.instance.restaurant = self.request.user.restaurant
        return super().form_valid(form)


class FoodItemCreateView(CreateView):
    model = FoodItem
    form_class = FoodItemForm
    template_name = 'restaurant/fooditem_form.html'
    success_url = reverse_lazy('dashboard')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['category'].queryset = Category.objects.filter(restaurant=self.request.user.restaurant)
        return form

    def form_valid(self, form):
        if form.cleaned_data['category'].restaurant != self.request.user.restaurant:
            messages.error(self.request, "Invalid category.")
            return self.form_invalid(form)
        return super().form_valid(form)


class FoodItemUpdateView(UpdateView):
    model = FoodItem
    fields = ['category', 'name', 'price', 'description', 'image']
    template_name = 'restaurant/fooditem_form.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        if form.instance.category.restaurant != self.request.user.restaurant:
            messages.error(self.request, "Unauthorized.")
            return self.form_invalid(form)
        return super().form_valid(form)


class FoodItemDeleteView(DeleteView):
    model = FoodItem
    template_name = 'restaurant/fooditem_confirm_delete.html'
    success_url = reverse_lazy('dashboard')

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.category.restaurant != request.user.restaurant:
            messages.error(request, "Unauthorized.")
            return redirect('dashboard')
        return super().delete(request, *args, **kwargs)


@login_required
def create_table_qr_view(request):
    restaurant = get_object_or_404(Restaurant, owner=request.user)
    tables = Table.objects.filter(restaurant=restaurant).order_by('table_number')
    return render(request, 'restaurant/create_table_qr.html', {"tables": tables})


def generate_qr_code(table):
    if not table.qr_code:
        qr = qrcode.QRCode(box_size=10, border=4)
        local_url = f"http://127.0.0.1:8000/menu/{table.restaurant.id}/{table.id}/"
        qr.add_data(local_url)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')

        folder = os.path.join(settings.MEDIA_ROOT, 'qr_codes', f'restaurant_{table.restaurant.id}')
        os.makedirs(folder, exist_ok=True)
        file_path = os.path.join(folder, f'table_{table.table_number}_qr.png')
        img.save(file_path)
        table.qr_code.name = f'qr_codes/restaurant_{table.restaurant.id}/table_{table.table_number}_qr.png'
        table.save()


def download_qr_code(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    if not table.qr_code:
        raise Http404("QR Code not found.")
    qr_path = os.path.join(settings.MEDIA_ROOT, table.qr_code.name)
    if not os.path.exists(qr_path):
        raise Http404("QR Code file missing.")
    return FileResponse(open(qr_path, "rb"), content_type="image/png")


# ---------------------------
# Menu & Orders
# ---------------------------
@login_required
def menu_preview(request):
    try:
        restaurant = request.user.restaurant
    except Restaurant.DoesNotExist:
        return render(request, 'restaurant/menu_preview.html', {'restaurant': None, 'tables': [], 'categories': []})

    tables = Table.objects.filter(restaurant=restaurant)
    categories = Category.objects.filter(restaurant=restaurant).prefetch_related('fooditem_set')

    return render(request, 'restaurant/menu_preview.html', {
        'restaurant': restaurant, 'tables': tables, 'categories': categories
    })


@login_required
def menu_view(request, restaurant_id, table_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    categories = Category.objects.filter(restaurant=restaurant)
    food_items = FoodItem.objects.filter(category__restaurant=restaurant)
    return render(request, 'restaurant/menu.html', {
        'restaurant': restaurant, 'table': table, 'categories': categories, 'food_items': food_items
    })


# ---------------------------
# Product detail
# ---------------------------
@require_http_methods(["GET", "POST"])
def product_detail_view(request, restaurant_id, table_id, pk):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    item = get_object_or_404(FoodItem, id=pk, category__restaurant=restaurant)

    if request.method == 'POST':
        order, _ = _get_or_create_single_open_order(table, restaurant)
        qty = int(request.POST.get('quantity', 1))
        oi = OrderItem.objects.create(order=order, food_item=item, quantity=qty)
        addon_ids = request.POST.getlist('addons')
        if addon_ids:
            addons = AddOn.objects.filter(id__in=addon_ids)
            oi.selected_addons.set(addons)
        return redirect('order_confirmation', order_id=order.id)

    addons = item.addons.all()
    return render(request, 'restaurant/product_detail.html', {
        'restaurant': restaurant, 'table': table, 'item': item, 'addons': addons,
    })


def product_detail(request, restaurant_id, table_id, pk):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    fooditem = get_object_or_404(FoodItem, id=pk, category__restaurant=restaurant)

    if request.method == "POST":
        qty = int(request.POST.get("quantity", 1))
        order, _ = _get_or_create_single_open_order(table, restaurant)
        OrderItem.objects.create(order=order, food_item=fooditem, quantity=qty)
        return redirect("order_confirmation", order_id=order.id)

    return render(request, "restaurant/product_detail.html", {
        "restaurant": restaurant, "table": table, "fooditem": fooditem
    })


def product_json(request, restaurant_id, table_id, pk):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    item = get_object_or_404(FoodItem, id=pk, category__restaurant=restaurant)

    addons = [{"id": a.id, "name": a.name, "price": float(a.price)} for a in item.addons.all()]
    data = {
        "id": item.id, "name": item.name, "description": item.description or "",
        "price": float(item.price), "image_url": item.image.url if item.image else None, "addons": addons
    }
    return JsonResponse(data)


# ---------------------------
# Cart AJAX
# ---------------------------
@require_POST
def add_to_cart_ajax(request, restaurant_id, table_id, pk):
    try:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
        table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
        item = get_object_or_404(FoodItem, id=pk, category__restaurant=restaurant)

        qty = int(request.POST.get('quantity', 1) or 1)
        raw_addons = request.POST.getlist('addons[]') or request.POST.getlist('addons') or []
        addon_ids = [int(a) for a in raw_addons if a.isdigit()]
        addons_qs = AddOn.objects.filter(id__in=addon_ids) if addon_ids else AddOn.objects.none()

        order, _ = _get_or_create_single_open_order(table, restaurant)
        oi = OrderItem.objects.create(order=order, food_item=item, quantity=qty)
        if addons_qs.exists():
            oi.selected_addons.set(addons_qs)

        total_price, total_count = 0, 0
        for it in order.order_items.all():
            base = float(it.food_item.price or 0) * it.quantity
            addons_price = sum(float(a.price) for a in it.selected_addons.all()) * it.quantity
            total_price += base + addons_price
            total_count += it.quantity

        line_base = float(item.price or 0) * oi.quantity
        line_addons = sum(float(a.price or 0) for a in oi.selected_addons.all()) * oi.quantity
        line_total = line_base + line_addons

        return JsonResponse({
            'success': True, 'message': 'Added to cart', 'order_id': order.id,
            'items_count': total_count, 'total_price': total_price, 'line_total': line_total
        })
    except Exception as exc:
        logger.exception("add_to_cart_ajax error")
        return JsonResponse({'success': False, 'message': 'Server error', 'traceback': traceback.format_exc()}, status=500)


def cart_summary(request, restaurant_id, table_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    order = Order.objects.filter(table=table, restaurant=restaurant, is_completed=False).first()
    if not order:
        return JsonResponse({'success': True, 'items_count': 0, 'total_price': 0.0})

    total_price, total_count = 0, 0
    for it in order.order_items.all():
        base = float(it.food_item.price or 0) * it.quantity
        addons_price = sum(float(a.price) for a in it.selected_addons.all()) * it.quantity
        total_price += base + addons_price
        total_count += it.quantity
    return JsonResponse({'success': True, 'items_count': total_count, 'total_price': total_price, 'order_id': order.id})


@require_POST
def place_cart_order(request, restaurant_id, table_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    order = Order.objects.filter(table=table, restaurant=restaurant, is_completed=False).first()
    if not order:
        messages.error(request, "Your cart is empty.")
        return redirect('menu_view', restaurant_id=restaurant.id, table_id=table.id)
    return redirect('order_confirmation', order_id=order.id)


# ---------------------------
# Order confirmation
# ---------------------------
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = order.order_items.prefetch_related("selected_addons", "food_item")
    total_price = 0
    for item in order_items:
        base_price = float(item.food_item.price or 0) * item.quantity
        addons_price = sum(float(a.price) for a in item.selected_addons.all()) * item.quantity
        item.item_total = base_price + addons_price
        total_price += item.item_total
    if request.method == "POST":
        return redirect('menu_view', restaurant_id=order.restaurant.id, table_id=order.table.id)
    return render(request, 'restaurant/order_confirmation.html', {
        'order': order, 'order_items': order_items, 'total_price': total_price
    })


# ---------------------------
# Delete / Confirm / Cancel
# ---------------------------
@require_POST
def delete_order_item_ajax(request, order_item_id):
    oi = get_object_or_404(OrderItem, id=order_item_id)
    order = oi.order
    oi.delete()
    total_price, total_count = 0, 0
    for it in order.order_items.all():
        base = float(it.food_item.price or 0) * it.quantity
        addons_price = sum(float(a.price) for a in it.selected_addons.all()) * it.quantity
        total_price += base + addons_price
        total_count += it.quantity
    return JsonResponse({'success': True, 'items_count': total_count, 'total_price': total_price, 'order_id': order.id})


@require_POST
def confirm_order_ajax(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.is_completed = True
    order.save()
    return JsonResponse({'success': True, 'order_id': order.id, 'message': 'Order sent to kitchen'})


@require_POST
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    restaurant_id, table_id = order.restaurant.id, order.table.id
    order.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'redirect_url': reverse('menu_view', args=[restaurant_id, table_id])})
    return redirect(reverse('menu_view', args=[restaurant_id, table_id]))


# ---------------------------
# Kitchen views
# ---------------------------
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
    orders = (Order.objects.filter(restaurant=restaurant, is_completed=False)
              .prefetch_related('order_items__food_item', 'order_items__selected_addons', 'table')
              .annotate(total_price=total_expr).order_by('created_at'))
    for o in orders:
        o.local_time = timezone.localtime(o.created_at)
    return render(request, 'restaurant/kitchen.html', {'orders': orders})


@login_required
def orders_json(request):
    try:
        restaurant = request.user.restaurant
    except Restaurant.DoesNotExist:
        return JsonResponse({'success': True, 'orders': []})
    orders_qs = (Order.objects.filter(restaurant=restaurant, is_completed=False)
                 .prefetch_related('order_items__food_item', 'order_items__selected_addons', 'table')
                 .order_by('created_at'))
    data = []
    for order in orders_qs:
        items, total = [], 0.0
        for it in order.order_items.all():
            addons = [{'id': a.id, 'name': a.name, 'price': float(a.price)} for a in it.selected_addons.all()]
            line = float(it.food_item.price or 0) * it.quantity + sum(a['price'] for a in addons) * it.quantity
            total += line
            items.append({'id': it.id, 'name': it.food_item.name, 'quantity': it.quantity,
                          'addons': addons, 'line_total': line})
        data.append({'order_id': order.id, 'table_number': order.table.table_number if order.table else None,
                     'created_at': order.created_at.isoformat(), 'total': total, 'items': items})
    return JsonResponse({'success': True, 'orders': data})


@login_required
def complete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, restaurant=request.user.restaurant)
    order.is_completed = True
    order.save()
    return JsonResponse({'success': True, 'order_id': order.id})
