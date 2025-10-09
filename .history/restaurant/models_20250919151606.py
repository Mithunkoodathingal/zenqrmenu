from django.db import models
from django.contrib.auth.models import User

class Restaurant(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    about = models.TextField(default='Initial Listings')
    cover_image = models.ImageField(upload_to='restaurant_covers/', default='default-cover.jpg')

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

    def __str__(self):
        return self.name

class AddOn(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"{self.name} (+₹{self.price})"

class FoodItem(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='food_images/', null=True, blank=True)  # New field
    addons = models.ManyToManyField(AddOn, blank=True)


    def __str__(self):
        return self.name
    
class Order(models.Model):
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)

    def total_price(self):
        total = 0
        for item in self.order_items.all():
            base = (item.food_item.price or 0) * (item.quantity or 0)
            addons_price = sum((a.price or 0) for a in item.selected_addons.all()) * (item.quantity or 0)
            total += base + addons_price
        return total

    def __str__(self):
        return f"Order {self.id} for {self.table}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE)
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    selected_addons = models.ManyToManyField(AddOn, blank=True)

    def __str__(self):
        return f"{self.quantity}x {self.food_item.name} in Order {self.order.id}"
    
