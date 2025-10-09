# views.py

import qrcode
from io import BytesIO
from django.shortcuts import render
from django.http import FileResponse, Http404
from django.core.files import File
from django.contrib.auth.mixins import LoginRequiredMixin
import os
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods
import logging
import traceback
from django.conf import settings
from django.http import JsonResponse, HttpResponseServerError
from .forms import FoodItemForm
from django.views import View
from django.db.models import Sum, F
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LogoutView
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from subscription.models import Subscription
from .models import Restaurant, Table, Category, FoodItem, Order, OrderItem, AddOn
from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib.auth import login, logout
from subscription.models import Subscription 
from django.core.files.base import ContentFile
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse
# near top of views.py
from decimal import Decimal, InvalidOperation
from django.db import transaction
import logging
logger = logging.getLogger(__name__)


@login_required
def complete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, table__restaurant=request.user.restaurant)
    order.is_completed = True
    order.save()
    return JsonResponse({'success': True, 'order_id': order.id})


def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Log in the user after signup
            return redirect('dashboard')  # Redirect to home or dashboard
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
            cover_image = request.FILES.get('cover_image')
        )
            
        return redirect('dashboard')
    return render(request, 'restaurant/create_restaurant.html')


@login_required
def kitchen_interface(request):
    restaurant = request.user.restaurant

    # Fetch orders and calculate total price
    orders = (
        Order.objects
        .filter(table__restaurant=restaurant, is_completed=False)
        .annotate(total_price=Sum(F('order_items__quantity') * F('order_items__food_item__price')))
        .order_by('created_at')
    )

    for order in orders:
        order.local_time = timezone.localtime(order.created_at)  # Convert to IST


    context = {'orders': orders}
    return render(request, 'restaurant/kitchen.html', context)


def place_order(request, table_id):
    table = get_object_or_404(Table, id=table_id)

    if request.method == 'POST':
        # ✅ Assign the restaurant while creating the order
        order = Order.objects.create(table=table, restaurant=table.restaurant)

        for item_id in request.POST:
            if item_id.startswith("quantity_"):
                food_id = int(item_id.split("_")[1])  # Extract food item ID
                quantity = int(request.POST[item_id])  # Get quantity

                if quantity > 0:
                    food_item = get_object_or_404(FoodItem, id=food_id)
                    OrderItem.objects.create(order=order, food_item=food_item, quantity=quantity)  # ✅ Save correctly

        return redirect('order_confirmation', order_id=order.id)  # ✅ Redirect to order confirmation

    menu_items = FoodItem.objects.filter(category__restaurant=table.restaurant)
    return render(request, 'restaurant/menu.html', {'menu_items': menu_items, 'table': table})



# def order_confirmation(request, order_id): 
#     order = get_object_or_404(Order, id=order_id)
#     order_items = order.order_items.all()  # Get all items in the order
#     total_price = sum(item.food_item.price * item.quantity for item in order_items)

#     if request.method == "POST":  # If user clicks "Back to Menu"
#         return redirect('menu_view', restaurant_id=order.restaurant.id, table_id=order.table.id)

#     context = {
#         'order': order,
#         'order_items': order_items,
#         'total_price': total_price
#     }
#     return render(request, 'restaurant/order_confirmation.html', context)

def order_confirmation(request, order_id): 
    order = get_object_or_404(Order, id=order_id)
    order_items = order.order_items.prefetch_related("selected_addons", "food_item")

    total_price = 0
    for item in order_items:
        base_price = item.food_item.price * item.quantity
        addons_price = sum(addon.price for addon in item.selected_addons.all()) * item.quantity
        item.item_total = base_price + addons_price  # attach for template
        total_price += item.item_total

    if request.method == "POST":  
        return redirect('menu_view', restaurant_id=order.restaurant.id, table_id=order.table.id)

    context = {
        'order': order,
        'order_items': order_items,
        'total_price': total_price
    }
    return render(request, 'restaurant/order_confirmation.html', context)



def menu_view(request, restaurant_id, table_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)

    # # Check if the restaurant has an active subscription
    # subscription = getattr(restaurant, 'subscription', None)

    # if not subscription or not subscription.is_active:
    #     messages.error(request, "Your subscription has expired. Please renew to access the menu.")
    #     return redirect('subscription_plans')

    # # Check if the table count is within the subscribed plan's limit
    # allowed_tables = subscription.plan.table_limit
    # total_tables = restaurant.table_set.count()

    # if total_tables > allowed_tables:
    #     messages.error(request, f"Your plan allows up to {allowed_tables} tables, but you have {total_tables}. Please upgrade your plan.")
    #     return redirect('subscription_plans')

    # Fetch categories and food items for the menu
    categories = Category.objects.filter(restaurant=restaurant)
    food_items = FoodItem.objects.filter(category__restaurant=restaurant)

    context = {
        'restaurant': restaurant,
        'table': table,
        'categories': categories,
        'food_items': food_items
    }
    return render(request, 'restaurant/menu.html', context)


class TableCreateView(CreateView):
    model = Table
    fields = ['table_number']
    template_name = 'restaurant/table_form.html'
    success_url = reverse_lazy('create_table_qr')  # Redirect to dashboard after table creation

    def form_valid(self, form):
        restaurant = self.request.user.restaurant  # Get the restaurant of logged-in user
        form.instance.restaurant = restaurant  # Assign restaurant before saving

        # ✅ Check if the restaurant has a subscription
        # try:
        #     subscription = restaurant.subscription
        #     if not subscription.has_active_subscription():
        #         messages.error(self.request, "Your subscription is inactive. Please subscribe to create tables.")
        #         return redirect('subscription_plans')
        # except Subscription.DoesNotExist:
        #     messages.error(self.request, "No active subscription found. Please subscribe to continue.")
        #     return redirect('subscription_plans')

        # If subscription is active, proceed with table creation
        response = super().form_valid(form)
        generate_qr_code(self.object)  # Generate QR code for the new table
        return response

    success_url = reverse_lazy('create_table_qr')

class CategoryCreateView(CreateView):
    model = Category
    fields = ['name']
    template_name = 'restaurant/category_form.html'
    
    def form_valid(self, form):
        form.instance.restaurant = self.request.user.restaurant
        return super().form_valid(form)
    
    success_url = reverse_lazy('dashboard')


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

        # Save FoodItem first
        response = super().form_valid(form)

        # Handle AddOns from hidden JSON input
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

    

@login_required
def dashboard(request):
    try:
        restaurant = request.user.restaurant
    except Restaurant.DoesNotExist:
        return render(request, 'restaurant/create_restaurant.html')

    # ✅ Check if the restaurant has an active subscription
    has_subscription = False
    try:
        subscription = restaurant.subscription
        if subscription and subscription.has_active_subscription():
            has_subscription = True
    except Subscription.DoesNotExist:
        has_subscription = False

    # Fetch categories and tables for the logged-in restaurant
    categories = Category.objects.filter(restaurant=restaurant)
    tables = Table.objects.filter(restaurant=restaurant)

    context = {
        'restaurant': restaurant,
        'tables': tables,
        'categories': categories,
        'has_subscription': has_subscription,  # ✅ Pass subscription status to the template
    }
    return render(request, 'restaurant/manage_menu.html', context)




def generate_qr_code(table):
    """Generate and save a unique QR code for the given Table instance."""
    if not table.qr_code:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # Ensure restaurant has a valid ID
        if not table.restaurant or not table.restaurant.id:
            raise ValueError("Table must be associated with a valid restaurant.")
        
        # ✅ Corrected URL format with `:8000`
        local_url = f"http://127.0.0.1:8000/menu/{table.restaurant.id}/{table.id}/"
        
        qr.add_data(local_url)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')

        # Save QR code inside the media folder
        qr_folder = os.path.join(settings.MEDIA_ROOT, 'qr_codes', f'restaurant_{table.restaurant.id}')
        os.makedirs(qr_folder, exist_ok=True)  # Ensure the folder exists

        file_path = os.path.join(qr_folder, f'table_{table.table_number}_qr.png')
        img.save(file_path)  # Save QR code as a file

        # Save the relative path to the model
        table.qr_code.name = f'qr_codes/restaurant_{table.restaurant.id}/table_{table.table_number}_qr.png'
        table.save()

def download_qr_code(request, table_id):
    """Serve the QR code as a downloadable file."""
    try:
        table = Table.objects.get(id=table_id)
        if not table.qr_code:  # Check if QR code exists
            raise Http404("QR Code not found.")

        qr_path = os.path.join(settings.MEDIA_ROOT, table.qr_code.name)

        if not os.path.exists(qr_path):
            raise Http404("QR Code file missing.")

        # Serve the file as an attachment
        response = FileResponse(open(qr_path, "rb"), content_type="image/png")
        response["Content-Disposition"] = f'attachment; filename="table_{table.table_number}_qr.png"'
        return response

    except Table.DoesNotExist:
        raise Http404("Table not found.")
    
# ✅ Update View
class FoodItemUpdateView(LoginRequiredMixin, UpdateView):
    model = FoodItem
    fields = ['category', 'name', 'price', 'description', 'image']
    template_name = 'restaurant/fooditem_form.html'
    
    def get_success_url(self):
        messages.success(self.request, "Food item updated successfully!")
        return reverse_lazy('dashboard')

    def form_valid(self, form):
        """Ensure only the restaurant owner can update items"""
        food_item = form.instance
        if food_item.category.restaurant != self.request.user.restaurant:
            messages.error(self.request, "Unauthorized action.")
            return self.form_invalid(form)
        return super().form_valid(form)

# ✅ Delete View
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

# def cancel_order(request, order_id):
#     order = get_object_or_404(Order, id=order_id)
#     restaurant_id = order.restaurant.id  # Extract restaurant ID
#     table_id = order.table.id  # Extract table ID

#     if request.method == "POST":
#         # Delete the order
#         order.delete()
#         messages.success(request, "Your order has been canceled successfully.")
#         return redirect(reverse('menu_view', args=[restaurant_id, table_id]))  # ✅ Correct redirect

#     return redirect('order_confirmation', order_id=order_id)



@login_required
def create_table_qr_view(request):
    restaurant = get_object_or_404(Restaurant, owner=request.user)  # safer
    tables = Table.objects.filter(restaurant=restaurant).order_by('table_number')
    return render(request, 'restaurant/create_table_qr.html', {"tables": tables})



@login_required
def menu_preview(request):
    try:
        restaurant = request.user.restaurant
        tables = Table.objects.filter(restaurant=restaurant)
        categories = Category.objects.filter(restaurant=restaurant).prefetch_related('fooditem_set')

        context = {
            'restaurant': restaurant,
            'tables': tables,
            'categories': categories
        }
        return render(request, 'restaurant/menu_preview.html', context)
    except Restaurant.DoesNotExist:
        return render(request, 'restaurant/menu_preview.html', {
            'restaurant': None,
            'tables': [],
            'categories': []
        })




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
    """
    GET: render product detail page
    POST: add the item (with addons/quantity) to an Order for the table (creates order if needed)
    """
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    item = get_object_or_404(FoodItem, id=pk, category__restaurant=restaurant)

    if request.method == 'POST':
        # Create or reuse an "open" order for this table
        order = Order.objects.create(table=table, restaurant=restaurant)
        # For now we add single OrderItem using posted quantity and addons
        qty = int(request.POST.get('quantity', 1))
        oi = OrderItem.objects.create(order=order, food_item=item, quantity=qty)
        # Add addons
        addon_ids = request.POST.getlist('addons')
        if addon_ids:
            addons = AddOn.objects.filter(id__in=addon_ids)
            oi.selected_addons.set(addons)
        return redirect('order_confirmation', order_id=order.id)

    # GET -> render detail
    addons = item.addons.all()
    return render(request, 'restaurant/product_detail.html', {
        'restaurant': restaurant,
        'table': table,
        'item': item,
        'addons': addons,
    })


from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect

def _get_or_create_open_order(table, restaurant):
    """
    Return an existing open (is_completed=False) order for the table + restaurant,
    or create a new one.
    """
    order = Order.objects.filter(table=table, restaurant=restaurant, is_completed=False).first()
    if order:
        return order
    return Order.objects.create(table=table, restaurant=restaurant)


def product_json(request, restaurant_id, table_id, pk):
    """Return item info + addons as JSON (used by modal)."""
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




logger = logging.getLogger(__name__)


@require_POST
def add_to_cart_ajax(request, restaurant_id, table_id, pk):
    """
    AJAX endpoint: add item to a single open order for the table.
    Returns JSON with numeric totals (floats) for client consumption.
    """
    try:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
        table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
        item = get_object_or_404(FoodItem, id=pk, category__restaurant=restaurant)

        # quantity parse (defensive)
        try:
            qty = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            qty = 1
        if qty < 1:
            qty = 1

        # handle addons[] or addons
        raw_addons = request.POST.getlist('addons[]') or request.POST.getlist('addons') or []
        if isinstance(raw_addons, str):
            raw_addons = [raw_addons]

        addon_ids = []
        for a in raw_addons:
            try:
                addon_ids.append(int(a))
            except (ValueError, TypeError):
                logger.warning("Invalid addon id ignored: %r", a)

        addons_qs = AddOn.objects.filter(id__in=addon_ids) if addon_ids else AddOn.objects.none()

        # get or create a single open order (merging duplicates if present)
        order, created = _get_or_create_single_open_order(table, restaurant)

        # create the order item
        oi = OrderItem.objects.create(order=order, food_item=item, quantity=qty)

        if addons_qs.exists():
            oi.selected_addons.set(addons_qs)

        # compute totals using Decimal to avoid float/Decimal mixing
        total_price = Decimal('0.00')
        total_count = 0
        for it in order.order_items.select_related('food_item').prefetch_related('selected_addons').all():
            base = (it.food_item.price or Decimal('0.00')) * (it.quantity or 0)
            addons_price = sum((a.price or Decimal('0.00')) for a in it.selected_addons.all()) * (it.quantity or 0)
            # coerce to Decimal
            try:
                total_price += Decimal(base) + Decimal(addons_price)
            except (InvalidOperation, TypeError):
                # in case base/addons_price are floats, convert safely
                total_price += Decimal(str(base)) + Decimal(str(addons_price))
            total_count += (it.quantity or 0)

        # line total for the inserted item
        line_base = (item.price or Decimal('0.00')) * oi.quantity
        line_addons = sum((a.price or Decimal('0.00')) for a in oi.selected_addons.all()) * oi.quantity
        try:
            line_total = Decimal(line_base) + Decimal(line_addons)
        except (InvalidOperation, TypeError):
            line_total = Decimal(str(line_base)) + Decimal(str(line_addons))

        # prepare JSON response (convert Decimal -> float)
        return JsonResponse({
            'success': True,
            'message': 'Added to cart',
            'order_id': order.id,
            'items_count': int(total_count),
            'total_price': float(total_price),    # safe for JS
            'line_total': float(line_total),
        })

    except Exception as exc:
        tb = traceback.format_exc()
        logger.exception("add_to_cart_ajax error: %s", exc)
        if settings.DEBUG:
            return JsonResponse({'success': False, 'message': 'Server error', 'traceback': tb}, status=500)
        return JsonResponse({'success': False, 'message': 'Server error, try again'}, status=500)



def cart_summary(request, restaurant_id, table_id):
    """
    Return JSON summary of the open order (items_count, total_price) for the menu mini-cart.
    """
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)

    # pick a single open order if multiple — merge duplicates first
    order, _ = _get_or_create_single_open_order(table, restaurant) if Order.objects.filter(table=table, restaurant=restaurant, is_completed=False).count() else (None, False)

    if not order:
        return JsonResponse({'success': True, 'items_count': 0, 'total_price': 0.0})

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
    """
    Finalize / place the current open order and redirect to order_confirmation.
    (We keep the order as is; placing simply redirects the user to the confirmation view where they can cancel/back.)
    """
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)

    order = Order.objects.filter(table=table, restaurant=restaurant, is_completed=False).first()
    if not order:
        # No items — redirect back to menu with message (or create empty order)
        messages.error(request, "Your cart is empty.")
        return redirect('menu_view', restaurant_id=restaurant.id, table_id=table.id)

    # Here we do not mark order completed; allow confirmation page to show and the restaurant to accept.
    return redirect('order_confirmation', order_id=order.id)


@require_POST
def cancel_order(request, order_id):
    """Cancel an order. If called via AJAX, return JSON so client can update UI without full reload."""
    order = get_object_or_404(Order, id=order_id)

    # You might want to add permission checks here (owner / restaurant / table)
    restaurant_id = order.restaurant.id
    table_id = order.table.id

    # Delete the order
    order.delete()

    # If AJAX request, return JSON so client-side can clear cart and redirect
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({'success': True, 'order_id': order_id, 'redirect_url': reverse('menu_view', args=[restaurant_id, table_id])})

    # Otherwise behave as before (POST from normal form)
    messages.success(request, "Your order has been canceled successfully.")
    return redirect(reverse('menu_view', args=[restaurant_id, table_id]))


# views.py (improved debug-friendly version)
import logging
import traceback
from django.conf import settings
from django.http import HttpResponse, HttpResponseServerError
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

def product_detail_html(request, restaurant_id, table_id, pk):
    """
    Return rendered HTML fragment for product detail (suitable to inject into a modal).
    Returns helpful error body in DEBUG to help debug 500s.
    """
    try:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
        table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
        item = get_object_or_404(FoodItem, id=pk, category__restaurant=restaurant)
        addons = item.addons.all()  # adjust if your relation name differs

        html = render_to_string(
            'restaurant/product_detail_fragment.html',
            {'restaurant': restaurant, 'table': table, 'item': item, 'addons': addons},
            request=request
        )
        return HttpResponse(html)

    except Exception as exc:
        # log the exception server-side
        logger.exception("product_detail_html failed for item %s (table %s, rest %s)", pk, table_id, restaurant_id)

        # Return detailed traceback in DEBUG to help you debug quickly.
        if settings.DEBUG:
            tb = traceback.format_exc()
            return HttpResponseServerError("<pre>Template/render error:\n\n{}</pre>".format(tb))
        else:
            # generic friendly message in production
            return HttpResponseServerError("Could not render product details. Please try again.")

def _get_or_create_single_open_order(table, restaurant):
    """
    Return a single open Order for (table, restaurant). If multiple open orders
    exist, merge them into the oldest one and remove duplicates.
    """
    # Get all open orders
    open_qs = Order.objects.filter(table=table, restaurant=restaurant, is_completed=False).order_by('created_at')
    if not open_qs.exists():
        # none -> create
        return Order.objects.create(table=table, restaurant=restaurant), True

    # at least one exists; pick the oldest as canonical
    canonical = open_qs.first()
    duplicates = list(open_qs[1:])  # others to merge/delete

    if duplicates:
        logger.warning("Merging %d duplicate open orders into order id=%s for table=%s",
                       len(duplicates), canonical.id, table.id)
        # Move each OrderItem from duplicates into canonical
        with transaction.atomic():
            for dup in duplicates:
                for oi in dup.order_items.all():
                    # try to find existing orderitem with same food_item and same selected_addons set
                    existing = None
                    # build set of addon ids for comparison
                    dup_addon_ids = set(oi.selected_addons.values_list('id', flat=True))
                    for e in canonical.order_items.filter(food_item=oi.food_item):
                        e_addon_ids = set(e.selected_addons.values_list('id', flat=True))
                        if e_addon_ids == dup_addon_ids:
                            existing = e
                            break
                    if existing:
                        # same item + same addons -> increment quantity
                        existing.quantity = (existing.quantity or 0) + (oi.quantity or 0)
                        existing.save()
                    else:
                        # re-parent the orderitem to canonical
                        oi.order = canonical
                        oi.save()
                # after moving items, delete the duplicate order
                dup.delete()
    return canonical, False

from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone

@require_POST
def delete_order_item_ajax(request, order_item_id):
    """
    Delete a specific OrderItem and return updated summary (items_count, total_price).
    """
    try:
        oi = get_object_or_404(OrderItem, id=order_item_id)
        order = oi.order
        # Optionally: security check: ensure this order belongs to the table/restaurant in context
        # If you want to require the user to be on same table, you could verify request path data.
        oi.delete()

        # recompute totals
        total_price = 0.0
        total_count = 0
        for it in order.order_items.select_related('food_item').prefetch_related('selected_addons').all():
            base = float(it.food_item.price or 0) * (it.quantity or 0)
            addons_price = sum(float(a.price or 0) for a in it.selected_addons.all()) * (it.quantity or 0)
            total_price += base + addons_price
            total_count += (it.quantity or 0)

        return JsonResponse({'success': True, 'items_count': total_count, 'total_price': float(total_price)})
    except Exception as exc:
        # helpful debug info when DEBUG=True
        if settings.DEBUG:
            import traceback
            tb = traceback.format_exc()
            return JsonResponse({'success': False, 'message': str(exc), 'traceback': tb}, status=500)
        return JsonResponse({'success': False, 'message': 'Could not delete item'}, status=500)


@require_POST
def confirm_order_ajax(request, order_id):
    """
    Confirm (place) the order — we update created_at so kitchen interfaces (which list is_completed=False orders)
    will see the order freshly sorted by created_at. Returns updated summary.
    """
    try:
        order = get_object_or_404(Order, id=order_id)
        # mark "placed now" by updating created_at
        order.created_at = timezone.now()
        order.save()

        # recompute totals
        total_price = 0.0
        total_count = 0
        for it in order.order_items.select_related('food_item').prefetch_related('selected_addons').all():
            base = float(it.food_item.price or 0) * (it.quantity or 0)
            addons_price = sum(float(a.price or 0) for a in it.selected_addons.all()) * (it.quantity or 0)
            total_price += base + addons_price
            total_count += (it.quantity or 0)

        return JsonResponse({'success': True, 'order_id': order.id, 'items_count': total_count, 'total_price': float(total_price)})
    except Exception as exc:
        if settings.DEBUG:
            import traceback
            tb = traceback.format_exc()
            return JsonResponse({'success': False, 'message': str(exc), 'traceback': tb}, status=500)
        return JsonResponse({'success': False, 'message': 'Could not confirm order'}, status=500)
