# restaurant/models.py

from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth.models import User
import random
import string
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
    cuisine_type = models.CharField(max_length=100, blank=True)

    default_payment_gateway = models.CharField(
        max_length=20,
        choices=[
            ("razorpay", "Razorpay"),
            ("stripe", "Stripe"),
            ("cash", "Cash"),
        ],
        default="razorpay"
    )

    tax_enabled = models.BooleanField(
        default=True
    )

    tax_name = models.CharField(
        max_length=50,
        default="GST",
        help_text="GST, VAT, Sales Tax, etc."
    )

    tax_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("5.00")
    )

    prices_include_tax = models.BooleanField(
        default=False
    )


    city = models.CharField(
        max_length=100
    )

    state = models.CharField(
        max_length=100
    )

    country = models.CharField(
        max_length=100,
        default="India",
    )

    pincode = models.CharField(
        max_length=10
    )

    phone_country_code = models.CharField(
        max_length=5,
        default="+91"
    )
    
    phone = models.CharField(
        max_length=20
    )

    alternate_phone = models.CharField(
        max_length=20,
        blank=True
    )

    email = models.EmailField(
        blank=True
    )

    website = models.URLField(
        blank=True
    )

    tax_registration_number = models.CharField(
        max_length=25,
        blank=True
    )

    fssai_number = models.CharField(
        max_length=30,
        blank=True
    )

    cgst_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2.50
    )

    sgst_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2.50
    )

    igst_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.00
    )

    invoice_prefix = models.CharField(
        max_length=20,
        default="INV"
    )

    currency_code = models.CharField(
        max_length=5,
        default="INR"
    )

    currency_symbol = models.CharField(
        max_length=5,
        default="₹"
    )

    footer_message = models.TextField(
        blank=True
    )

    timezone = models.CharField(
        max_length=50,
        default="Asia/Kolkata"
    )

    currency_decimal_places = models.PositiveSmallIntegerField(
        default=2
    )

    # ==========================================
    # DELIVERY SETTINGS
    # ==========================================

    delivery_enabled = models.BooleanField(
        default=False
    )

    pickup_enabled = models.BooleanField(
        default=False
    )

    cash_on_delivery = models.BooleanField(
        default=False
    )

    cash_on_pickup = models.BooleanField(
        default=True
    )

    delivery_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )

    delivery_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )

    free_delivery_radius_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=3
    )

    maximum_delivery_radius_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=10
    )

    delivery_charge_per_km = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00")
    )

    minimum_delivery_order = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00")
    )

    average_preparation_time = models.PositiveIntegerField(
        default=20,
        help_text="Minutes"
    )
    class Meta:

        indexes = [

            models.Index(fields=["owner"]),

            models.Index(fields=["delivery_enabled"]),

            models.Index(fields=["pickup_enabled"]),

        ]

    def __str__(self):
        return self.name

class Table(models.Model):
    restaurant = models.ForeignKey(Restaurant, related_name="tables", on_delete=models.CASCADE)
    table_number = models.IntegerField()
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "table_number"],
                name="unique_table_per_restaurant",
            )
        ] # Ensure table number is unique per restaurant

    def __str__(self):
        return f"Table {self.table_number} at {self.restaurant.name}"

class Category(models.Model):
    restaurant = models.ForeignKey(Restaurant, related_name="categories", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    # class Meta:
    #     unique_together = ['name', 'restaurant']

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "restaurant"],
                name="unique_category_per_restaurant",
            )
        ]

    def __str__(self):
        return self.name

class AddOn(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"{self.name} (+₹{self.price})"

class FoodItem(models.Model):
    restaurant = models.ForeignKey(Restaurant, related_name="food_items", on_delete=models.CASCADE)
    category = models.ForeignKey(Category, related_name="food_items", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to=upload_food_image, null=True, blank=True)  # New field
    addons = models.ManyToManyField(AddOn, blank=True)
    is_veg = models.BooleanField(default=True)
    is_paused = models.BooleanField(default=False, help_text="When true, item is hidden from public menu (out of stock).")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "restaurant"],
                name="unique_food_item_per_restaurant",
            )
        ]

        indexes = [
            models.Index(fields=["restaurant"]),
            models.Index(fields=["category"]),
            models.Index(fields=["restaurant", "category"]),
            models.Index(fields=["is_paused"]),
        ]

    def __str__(self):
        return self.name
    
class Order(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),    
        ('ready', 'Ready'),
    ]


    ORDER_TYPES = [
        ("dinein", "Dine In"),
        ("pickup", "Pickup"),
        ("delivery", "Delivery"),
    ]

    order_type = models.CharField(
        max_length=20,
        choices=ORDER_TYPES,
        default="dinein",
        db_index=True,
    )

    PAYMENT_STATUS = [
        ("pending","Pending"),
        ("paid","Paid"),
        ("failed","Failed"),
        ("refunded","Refunded"),
    ]

    DELIVERY_STATUS = [
        ("not_required","Not Required"),
        ("assigned","Assigned"),
        ("picked","Picked"),
        ("out_for_delivery","Out for Delivery"),
        ("delivered","Delivered"),
    ]

    delivery_status = models.CharField(
        max_length=30,
        choices=DELIVERY_STATUS,
        default="not_required",
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default="pending",
    )
    
    delivery_distance_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00")
    )
    delivery_charge = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00")
    )
    scheduled_time = models.DateTimeField(
        null=True,
        blank=True
    )
    id = models.UUIDField( primary_key=True, default=uuid.uuid4, editable=False)

    restaurant = models.ForeignKey(Restaurant, related_name="orders", on_delete=models.CASCADE)
    
    customer_address = models.TextField(blank=True)

    customer_city = models.CharField(
        max_length=100,
        blank=True
    )

    customer_state = models.CharField(
        max_length=100,
        blank=True
    )

    customer_pincode = models.CharField(
        max_length=10,
        blank=True
    )
    delivery_latitude = models.DecimalField( max_digits=10, decimal_places=7, null=True, blank=True)
    delivery_longitude = models.DecimalField( max_digits=10, decimal_places=7, null=True, blank=True)
    order_number = models.CharField( max_length=25, unique=True, blank=True, db_index=True,)
    pickup_verified = models.BooleanField(default=False)
    delivery_verified = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    table = models.ForeignKey( Table, null=True, blank=True, related_name="orders", on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField( null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    total_price_cached = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    customer_name = models.CharField(max_length=150, blank=True, default='')
    customer_phone = models.CharField(max_length=20, blank=True, default='')
    customer_email = models.EmailField( blank=True)
    customer_note = models.TextField( blank=True )
    customer_country = models.CharField(
        max_length=100,
        default="India"
    )

    customer_country_code = models.CharField(
        max_length=6,
        default="+91"
    )

    # ==========================================
    # DELIVERY ASSIGNMENT
    # ==========================================

    delivery_person_name = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )

    delivery_person_phone = models.CharField(
        max_length=20,
        blank=True,
        default=""
    )

    # ==========================================
    # DELIVERY TIMELINE
    # ==========================================

    assigned_at = models.DateTimeField(
        null=True,
        blank=True
    )

    picked_at = models.DateTimeField(
        null=True,
        blank=True
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # ==========================================
    # PRINTING
    # ==========================================

    kitchen_printed = models.BooleanField(
        default=False
    )

    receipt_printed = models.BooleanField(
        default=False
    )


    #===========================================================


    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    packing_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    tip_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    round_off = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )

    grand_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    cgst = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    sgst = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    igst = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )


    # ==========================================
    # SOFT DELETE
    # ==========================================

    is_deleted = models.BooleanField(
        default=False
    )

    class Meta:

        ordering = ["-created_at"]

        indexes = [

            models.Index(fields=["restaurant"]),

            models.Index(fields=["status"]),

            models.Index(fields=["order_type"]),

            models.Index(fields=["payment_status"]),

            models.Index(fields=["delivery_status"]),

            models.Index(fields=["created_at"]),

            models.Index(fields=["customer_phone"]),

            models.Index(fields=["order_number"]),

            models.Index(fields=["is_completed"]),

            models.Index(fields=["is_deleted"]),

        ]

    def save(self, *args, **kwargs):

        if not self.order_number:
            while True:
                random_part = "".join(
                    random.choices(
                        string.ascii_uppercase + string.digits,
                        k=6
                    )
                )

                number = f"ORD-{timezone.now().strftime('%Y%m%d')}-{random_part}"

                if not Order.objects.filter(order_number=number).exists():
                    self.order_number = number
                    break

        if self.status == "completed":
            self.is_completed = True

            if not self.completed_at:
                self.completed_at = timezone.now()

        super().save(*args, **kwargs)


    @property
    def total_price(self):
        return self.total_price_cached
        
    # def total_price(self):
    #     total = 0
    #     for item in self.order_items.all():
    #         base = (item.food_item.price or 0) * (item.quantity or 0)
    #         addons_price = sum((a.price or 0) for a in item.selected_addons.all()) * (item.quantity or 0)
    #         total += base + addons_price
    #     return total

    def __str__(self):
        return f"{self.order_number} ({self.order_type})"
    
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
    
