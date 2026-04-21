# restaurant/models.py

from django.db import models
from django.contrib.auth.models import User

import uuid

def upload_logo(instance, filename):
    ext = filename.split('.')[-1]
    return f"restaurant_logos/{uuid.uuid4()}.{ext}"

def upload_cover(instance, filename):
    ext = filename.split('.')[-1]
    return f"restaurant_covers/{uuid.uuid4()}.{ext}"

def upload_food_image(instance, filename):
    ext = filename.split('.')[-1]
    return f"food_images/{uuid.uuid4()}.{ext}"

class Restaurant(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    about = models.TextField(default='Initial Listings')
    cover_image = models.ImageField( upload_to=upload_cover, default='default/default-cover.jpg')
    logo = models.ImageField( upload_to=upload_logo, blank=True, null=True, default='default/default-logo.png', help_text='Small square logo/profile image used as thumbnail on menus')
    phone = models.CharField(max_length=20, blank=True)
    cuisine_type = models.CharField(max_length=100, blank=True)


    def __str__(self):
        return self.name

class Table(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    table_number = models.IntegerField()
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)

    class Meta:
        unique_together = ('restaurant', 'table_number')  # Ensure table number is unique per restaurant

    def __str__(self):
        return f"Table {self.table_number} at {self.restaurant.name}"

class Category(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ['name', 'restaurant']

    def __str__(self):
        return self.name

class AddOn(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"{self.name} (+₹{self.price})"

class FoodItem(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to=upload_food_image, null=True, blank=True)  # New field
    addons = models.ManyToManyField(AddOn, blank=True)
    is_veg = models.BooleanField(default=True)
    is_paused = models.BooleanField(default=False, help_text="When true, item is hidden from public menu (out of stock).")

    class Meta:
        indexes = [
            models.Index(fields=['restaurant']),
        ]

    class Meta:
        unique_together = ['name', 'restaurant']

    def __str__(self):
        return self.name
    
class Order(models.Model):
    STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('confirmed', 'Confirmed'),
    ('preparing', 'Preparing'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    total_price_cached = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    customer_name = models.CharField(max_length=100, blank=True, default='')
    customer_phone = models.CharField(max_length=15, blank=True, default='')

    def save(self, *args, **kwargs):
        if self.status == 'completed':
            self.is_completed = True
        super().save(*args, **kwargs)

    def total_price(self):
        total = 0
        for item in self.order_items.all():
            base = (item.food_item.price or 0) * (item.quantity or 0)
            addons_price = sum((a.price or 0) for a in item.selected_addons.all()) * (item.quantity or 0)
            total += base + addons_price
        return total

    def __str__(self):
        return f"Order {self.id} for {self.table}"
    
    def update_total(self):
        total = 0
        for item in self.order_items.all():
            base = (item.food_item.price or 0) * (item.quantity or 0)
            addons_price = sum((a.price or 0) for a in item.selected_addons.all()) * (item.quantity or 0)
            total += base + addons_price
        self.total_price_cached = total
        self.save(update_fields=['total_price_cached'])

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE)
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    selected_addons = models.ManyToManyField(AddOn, blank=True)

    def __str__(self):
        return f"{self.quantity}x {self.food_item.name} in Order {self.order.id}"
    
