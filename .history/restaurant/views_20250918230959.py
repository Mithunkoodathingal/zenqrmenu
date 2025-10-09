import qrcode
from io import BytesIO
from django.shortcuts import render
from django.http import FileResponse, Http404
from django.core.files import File
from django.contrib.auth.mixins import LoginRequiredMixin
import os
from django.urls import reverse
from django.views.decorators.http import require_POST
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

def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    restaurant_id = order.restaurant.id  # Extract restaurant ID
    table_id = order.table.id  # Extract table ID

    if request.method == "POST":
        # Delete the order
        order.delete()
        messages.success(request, "Your order has been canceled successfully.")
        return redirect(reverse('menu_view', args=[restaurant_id, table_id]))  # ✅ Correct redirect

    return redirect('order_confirmation', order_id=order_id)



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
    food_item = get_object_or_404(FoodItem, id=pk, category__restaurant=restaurant)

    return render(request, "restaurant/product_detail.html", {
        "restaurant": restaurant,
        "table": table,
        "food_item": food_item,
    })


@require_POST
def add_to_order(request, restaurant_id, table_id, pk):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    food_item = get_object_or_404(FoodItem, id=pk, category__restaurant=restaurant)

    # Get/create ongoing order
    order, _ = Order.objects.get_or_create(table=table, restaurant=restaurant, is_completed=False)

    # Get quantity
    quantity = int(request.POST.get("quantity", 1))

    order_item = OrderItem.objects.create(order=order, food_item=food_item, quantity=quantity)

    # Handle add-ons
    addons = request.POST.getlist("addons")
    if addons:
        order_item.selected_addons.set(addons)

    order_item.save()

    messages.success(request, f"{food_item.name} added to order!")
    return redirect("menu_view", restaurant_id=restaurant.id, table_id=table.id)
