"""Shared helpers for the automated checks."""
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


def make_owner(username="owner", restaurant_name="Malabar Kitchen", **restaurant_fields):
    from restaurants.models import Restaurant
    user = get_user_model().objects.create_user(username, f"{username}@example.com", "pass12345!")
    restaurant = Restaurant.objects.create(
        owner=user, name=restaurant_name, phone="+919876543210", email=f"{username}@example.com",
        **restaurant_fields,
    )
    return user, restaurant


def owner_client(username="owner", **restaurant_fields):
    user, restaurant = make_owner(username, **restaurant_fields)
    client = APIClient()
    client.force_authenticate(user)
    return client, restaurant


ALWAYS_OPEN = {d: {"is_open": True, "open": "00:00", "close": "00:00"}
               for d in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}


def make_customer(email="diner@example.com", name="Asha"):
    """A signed-in, verified diner."""
    from customers.models import CustomerProfile
    user = get_user_model().objects.create_user(f"cust_{email.split('@')[0]}", email)
    profile = CustomerProfile.objects.create(user=user, email=email, name=name, phone="+919800000001", email_verified=True)
    client = APIClient()
    client.force_authenticate(user)
    return client, profile


def make_menu(restaurant, price="200.00", **item_fields):
    """One category, one item (with a ₹30 add-on) and one table at the main branch."""
    from menu.models import AddOn, Category, FoodItem
    from restaurants.models import Table
    restaurant.working_hours = {**ALWAYS_OPEN, "holidays": []}
    restaurant.latitude, restaurant.longitude = 11.2588, 75.7804
    restaurant.save()
    cat = Category.objects.create(restaurant=restaurant, name="Mains")
    item = FoodItem.objects.create(restaurant=restaurant, category=cat, name="Chicken Biryani", price=price, **item_fields)
    addon = AddOn.objects.create(food_item=item, name="Extra raita", price="30.00")
    table = Table.objects.create(restaurant=restaurant, branch=restaurant.main_branch(), table_number="1")
    return item, addon, table
