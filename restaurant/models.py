# restaurant/models.py

from copy import deepcopy

from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth.models import User
import random
import string
import uuid

from django.conf import settings

def upload_logo(instance, filename):
    ext = filename.split('.')[-1]
    return f"restaurant_logos/{uuid.uuid4()}.{ext}"

def upload_cover(instance, filename):
    ext = filename.split('.')[-1]
    return f"restaurant_covers/{uuid.uuid4()}.{ext}"

def upload_food_image(instance, filename):
    ext = filename.split('.')[-1]
    return f"food_images/{uuid.uuid4()}.{ext}"

# =============================================================================
# Restaurant Model
# =============================================================================

DEFAULT_WORKING_HOURS = {
    "monday": {
        "is_open": True,
        "open": "09:00",
        "close": "22:00",
    },
    "tuesday": {
        "is_open": True,
        "open": "09:00",
        "close": "22:00",
    },
    "wednesday": {
        "is_open": True,
        "open": "09:00",
        "close": "22:00",
    },
    "thursday": {
        "is_open": True,
        "open": "09:00",
        "close": "22:00",
    },
    "friday": {
        "is_open": True,
        "open": "09:00",
        "close": "22:00",
    },
    "saturday": {
        "is_open": True,
        "open": "09:00",
        "close": "22:00",
    },
    "sunday": {
        "is_open": False,
        "open": "09:00",
        "close": "22:00",
    },
}

def default_working_hours():
    
    return deepcopy(DEFAULT_WORKING_HOURS)


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
    
    working_hours = models.JSONField(
        
        default=default_working_hours,
        
        help_text="Weekly working schedule."
        
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
        max_length=100,
        default="Gotham",
    )

    state = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    country = models.CharField(
        max_length=100,
        default="India",
    )

    pincode = models.CharField(
        max_length=10,
        blank=True,
        null=True,
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
    
    # ==========================================
    # Status
    # ==========================================

    is_active = models.BooleanField(
        default=True,
    )

    is_deleted = models.BooleanField(
        default=False,
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    
    class Meta:

        indexes = [

            models.Index(fields=["owner"]),

            models.Index(fields=["delivery_enabled"]),

            models.Index(fields=["pickup_enabled"]),
            
            models.Index(fields=["is_active"]),
            
            models.Index(fields=["is_deleted"]),
            
            models.Index(fields=["owner", "is_deleted"]),

        ]

    def __str__(self):
        return self.name

# =============================================================================
# Table Model
# =============================================================================

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

# =============================================================================
# Category Model
# =============================================================================

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
# =============================================================================
# Add On Model
# =============================================================================

class AddOn(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"{self.name} (+₹{self.price})"

# =============================================================================
# Food Item Model
# =============================================================================

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
    
# =============================================================================
# Delivery Partner Model
# =============================================================================

class DeliveryPartner(models.Model):
    """
    Delivery Partner

    Represents a delivery executive belonging
    to a restaurant.

    Responsibilities

        • Delivery assignment

        • Live location

        • Contact details

        • Vehicle information

        • Availability

        • Performance tracking
    """

    # ==========================================================
    # Restaurant
    # ==========================================================

    restaurant = models.ForeignKey(

        Restaurant,

        on_delete=models.CASCADE,

        related_name="delivery_partners",

    )

    # ==========================================================
    # Identity
    # ==========================================================

    first_name = models.CharField(

        max_length=100,

    )

    last_name = models.CharField(

        max_length=100,

        blank=True,

    )

    profile_photo = models.ImageField(

        upload_to="delivery_partners/",

        blank=True,

        null=True,

    )

    # ==========================================================
    # Contact
    # ==========================================================

    country_code = models.CharField(

        max_length=5,

        default="+91",

    )

    phone = models.CharField(

        max_length=20,

        unique=True,

    )

    alternate_phone = models.CharField(

        max_length=20,

        blank=True,

    )

    email = models.EmailField(

        blank=True,

    )

    # ==========================================================
    # Address
    # ==========================================================

    address = models.TextField(

        blank=True,

    )

    city = models.CharField(

        max_length=100,

        blank=True,

    )

    state = models.CharField(

        max_length=100,

        blank=True,

    )

    pincode = models.CharField(
        max_length=10,
        blank=True,
        null=True,
    )

    # ==========================================================
    # Vehicle
    # ==========================================================

    vehicle_type = models.CharField(

        max_length=30,

        choices=[

            ("bike", "Bike"),

            ("cycle", "Cycle"),

            ("car", "Car"),

            ("scooter", "Scooter"),

        ],

        default="bike",

    )

    vehicle_number = models.CharField(

        max_length=20,

        blank=True,

    )

    driving_license_number = models.CharField(

        max_length=30,

        blank=True,

    )

    # ==========================================================
    # Status
    # ==========================================================

    is_active = models.BooleanField(

        default=True,

    )

    is_available = models.BooleanField(

        default=True,

    )

    is_verified = models.BooleanField(

        default=False,

    )

    # ==========================================================
    # Live Location
    # ==========================================================

    current_latitude = models.DecimalField(

        max_digits=10,

        decimal_places=7,

        null=True,

        blank=True,

    )

    current_longitude = models.DecimalField(

        max_digits=10,

        decimal_places=7,

        null=True,

        blank=True,

    )

    last_location_update = models.DateTimeField(

        null=True,

        blank=True,

    )

    # ==========================================================
    # Performance
    # ==========================================================

    total_deliveries = models.PositiveIntegerField(

        default=0,

    )

    successful_deliveries = models.PositiveIntegerField(

        default=0,

    )

    cancelled_deliveries = models.PositiveIntegerField(

        default=0,

    )

    average_rating = models.DecimalField(

        max_digits=3,

        decimal_places=2,

        default=Decimal("0.00"),

    )

    # ==========================================================
    # Employment
    # ==========================================================

    joined_at = models.DateTimeField(

        auto_now_add=True,

    )

    resigned_at = models.DateTimeField(

        null=True,

        blank=True,

    )

    notes = models.TextField(

        blank=True,

    )

    # ==========================================================
    # Audit
    # ==========================================================

    created_at = models.DateTimeField(

        auto_now_add=True,

    )

    updated_at = models.DateTimeField(

        auto_now=True,

    )

    class Meta:

        ordering = [

            "first_name",

        ]

        indexes = [

            models.Index(

                fields=["restaurant"],

            ),

            models.Index(

                fields=["phone"],

            ),

            models.Index(

                fields=["is_active"],

            ),

            models.Index(

                fields=["is_available"],

            ),

            models.Index(

                fields=[

                    "current_latitude",

                    "current_longitude",

                ],

            ),

        ]

    def __str__(self):

        return (

            f"{self.first_name} "

            f"{self.last_name}"

        ).strip()

    @property
    def full_name(self):

        return (

            f"{self.first_name} "

            f"{self.last_name}"

        ).strip()

    @property
    def success_rate(self):

        if self.total_deliveries == 0:

            return Decimal("0.00")

        return round(

            (

                self.successful_deliveries

                / self.total_deliveries

            ) * 100,

            2,

        )
        
# =============================================================================
# Staff Model
# =============================================================================

class Staff(models.Model):
    """
    Restaurant staff member.

    Used by

    • Kitchen

    • Cashier

    • Waiter

    • Inventory

    • Reviews

    • Reports

    • Audit Logs
    """

    # ==========================================================
    # Roles
    # ==========================================================

    ROLE_CHOICES = [

        ("owner", "Owner"),

        ("manager", "Manager"),

        ("chef", "Chef"),

        ("cashier", "Cashier"),

        ("waiter", "Waiter"),

        ("delivery_manager", "Delivery Manager"),

        ("inventory_manager", "Inventory Manager"),

    ]

    # ==========================================================
    # Restaurant
    # ==========================================================

    restaurant = models.ForeignKey(

        Restaurant,

        on_delete=models.CASCADE,

        related_name="staff_members",

    )

    # ==========================================================
    # User Account
    # ==========================================================

    user = models.OneToOneField(

        settings.AUTH_USER_MODEL,

        on_delete=models.CASCADE,

        null=True,

        blank=True,

        related_name="staff_profile",

    )

    # ==========================================================
    # Identity
    # ==========================================================

    employee_id = models.CharField(

        max_length=50,

    )

    first_name = models.CharField(

        max_length=100,

    )

    last_name = models.CharField(

        max_length=100,

        blank=True,

    )

    profile_photo = models.ImageField(

        upload_to="staff/",

        blank=True,

        null=True,

    )

    # ==========================================================
    # Contact
    # ==========================================================

    country_code = models.CharField(

        max_length=5,

        default="+91",

    )

    phone = models.CharField(

        max_length=20,

    )

    alternate_phone = models.CharField(

        max_length=20,

        blank=True,

    )

    email = models.EmailField(

        blank=True,

    )

    # ==========================================================
    # Employment
    # ==========================================================

    role = models.CharField(

        max_length=30,

        choices=ROLE_CHOICES,

        default="chef",

    )

    designation = models.CharField(

        max_length=100,

        blank=True,

    )

    joining_date = models.DateField(

        default=timezone.now,

    )

    salary = models.DecimalField(

        max_digits=10,

        decimal_places=2,

        null=True,
        
        blank=True,

    )
    

    # ==========================================================
    # Current Runtime State
    # ==========================================================

    is_on_shift = models.BooleanField(

        default=False,

    )

    is_on_break = models.BooleanField(

        default=False,

    )
    
    last_shift_started_at = models.DateTimeField(
        
        null=True,
        
        blank=True,
        
    )

    last_shift_ended_at = models.DateTimeField(
        
        null=True,
        
        blank=True,
        
    )

    # ==========================================================
    # Status
    # ==========================================================

    is_active = models.BooleanField(

        default=True,

    )
    
    is_deleted = models.BooleanField(
        
        default=False,
        
    )
    
    resigned_at = models.DateTimeField(
        
        null=True,
        
        blank=True,
        
    )
    
    notes = models.TextField(
        
        blank=True,
        
    )

    last_login_at = models.DateTimeField(

        null=True,

        blank=True,

    )    

    # ==========================================================
    # Audit
    # ==========================================================

    created_at = models.DateTimeField(

        auto_now_add=True,

    )

    updated_at = models.DateTimeField(

        auto_now=True,

    )

    
    # ==========================================================
    # Future Modules
    # ==========================================================
    #
    # Attendance
    # Payroll
    # Leave Requests
    # Permissions
    # OTP
    # Device Tracking
    #
    # These will be implemented as
    # separate models later.

    class Meta:

        ordering = [

            "first_name",

            "last_name",

        ]
        
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "employee_id"],
                name="unique_employee_per_restaurant",
            )
        ]


        indexes = [            
            
            models.Index(fields=["restaurant"]),

            models.Index(fields=["role"]),

            models.Index(fields=["is_active"]),

            models.Index(fields=["restaurant", "role"]),

            models.Index(fields=["restaurant", "is_active"]),

            models.Index(fields=["restaurant", "is_deleted"]),

        ]

    @property
    def full_name(self):

        return (

            f"{self.first_name} "

            f"{self.last_name}"

        ).strip()
        
    # ======================================
    
    @property
    def has_login(self):
        
        return self.user is not None
    
    # ======================================

    def __str__(self):

        return (

            f"{self.employee_id} - "

            f"{self.full_name}"

        )
        
# =============================================================================
# Order Model
# =============================================================================

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
        ("failed","Failed"),
    ]
    
    # ==========================================
    # KITCHEN TIMELINE
    # ==========================================
    
    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    kitchen_started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    kitchen_ready_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    served_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    
    kitchen_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("preparing", "Preparing"),
            ("ready", "Ready"),
            ("served", "Served"),
        ],
        default="pending",
    )

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
    kitchen_priority = models.CharField(
        max_length=20,
        choices=[
            ("low", "Low"),
            ("normal", "Normal"),
            ("high", "High"),
            ("urgent", "Urgent"),
        ],
        default="normal",
    )
    
    estimated_ready_time = models.DateTimeField(
        null=True,
        blank=True,
    )

    kitchen_notes = models.TextField(
        blank=True,
    )

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
    order_number = models.CharField(max_length=25, unique=True, blank=True, null=True, db_index=True,)
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

    delivery_partner = models.ForeignKey(

        DeliveryPartner,

        on_delete=models.SET_NULL,

        null=True,

        blank=True,

        related_name="orders",

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

    indexes = [

        models.Index(fields=["restaurant"]),

        models.Index(fields=["order_type"]),

        models.Index(fields=["payment_status"]),

        models.Index(fields=["delivery_status"]),

        models.Index(fields=["customer_phone"]),

        models.Index(fields=["order_number"]),

        models.Index(fields=["is_completed"]),

        models.Index(fields=["is_deleted"]),

        models.Index(fields=["kitchen_priority"]),

        models.Index(fields=["restaurant", "status"]),

        models.Index(fields=["restaurant", "created_at"]),

        models.Index(fields=["restaurant", "kitchen_status"]),

        models.Index(
            fields=[
                "restaurant",
                "kitchen_status",
                "kitchen_priority",
            ]
        ),

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
        
    @property
    def is_delivery(self):
        return self.order_type == "delivery"

    @property
    def is_pickup(self):
        return self.order_type == "pickup"

    @property
    def is_dinein(self):
        return self.order_type == "dinein"

    @property
    def is_paid(self):
        return self.payment_status == "paid"

    @property
    def is_ready(self):
        return self.kitchen_status == "ready"

# =============================================================================
# Order Item Model
# =============================================================================

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE)
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    selected_addons = models.ManyToManyField(AddOn, blank=True)

    def __str__(self):
        return f"{self.quantity}x {self.food_item.name} in Order {self.order.id}"
    
# =============================================================================
# Kitchen Notes
# =============================================================================

class KitchenNote(models.Model):
    """
    Stores kitchen notes/history for an order.
    """

    NOTE_TYPES = [

        ("general", "General"),

        ("customer", "Customer Request"),

        ("allergy", "Allergy"),

        ("chef", "Chef"),

        ("manager", "Manager"),

    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="kitchen_note_logs",
    )

    staff = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kitchen_note_logs",
    )

    note = models.TextField()
    
    note_type = models.CharField(
        max_length=20,
        choices=NOTE_TYPES,
        default="general",
    )
    
    # Managers can hide notes while preserving history.
    is_deleted = models.BooleanField(
        
        default=False,
    )
    
    is_pinned = models.BooleanField(
        default=False,
    )
    
    # Customer-visible vs internal kitchen notes.
    is_internal = models.BooleanField(
        default=True,
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    
    edited_by = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edited_kitchen_notes",
    )
    
    edited_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    
    edited_reason = models.CharField(
        max_length=255,
        blank=True,
    )
    
    class Meta:

        ordering = [

            "-is_pinned",

            "-created_at",

        ]

        indexes = [

            models.Index(
                fields=[
                    "order",
                    "is_deleted",
                ]
            ),

            models.Index(
                fields=[
                    "order",
                    "created_at",
                ]
            ),

            models.Index(
                fields=[
                    "order",
                    "is_pinned",
                ]
            ),

            models.Index(fields=["staff"]),

            models.Index(fields=["note_type"]),

            models.Index(fields=["is_deleted"]),

            models.Index(fields=["is_pinned"]),

            models.Index(fields=["is_internal"]),

        ]

    def __str__(self):

        return (

            f"{self.order.order_number}"

            f" | "

            f"{self.get_note_type_display()}"

            f" | "

            f"{self.note[:40]}"

        )
        
# =============================================================================
# Staff Attendance
# =============================================================================

class StaffAttendance(models.Model):  
    
    # ==========================================================
    # Attendance Status
    # ==========================================================

    STATUS_CHOICES = [

            ("present", "Present"),

            ("absent", "Absent"),

            ("half_day", "Half Day"),

            ("leave", "Leave"),

    ]
    
    # ==========================================================
    # Relationships
    # ==========================================================

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="staff_attendance",
    )

    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name="attendance_logs",
    )
    
    # ==========================================================
    # Attendance
    # ==========================================================

    attendance_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="present",
    )
    
    # ==========================================================
    # Working Hours
    # ==========================================================

    clock_in = models.DateTimeField(
        null=True,
        blank=True,
    )

    clock_out = models.DateTimeField(
        null=True,
        blank=True,
    )

    worked_minutes = models.PositiveIntegerField(
        default=0,
    )

    overtime_minutes = models.PositiveIntegerField(
        default=0,
    )

    late_minutes = models.PositiveIntegerField(
        default=0,
    )
    
    # ==========================================================
    # Break Summary
    # ==========================================================

    break_minutes = models.PositiveIntegerField(
        default=0,
    )
    
    # ==========================================================
    # Notes
    # ==========================================================

    notes = models.TextField(
        blank=True,
    )
    
    # ==========================================================
    # Soft Delete
    # ==========================================================

    is_deleted = models.BooleanField(
        default=False,
    )
    
    # ==========================================================
    # Audit
    # ==========================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )
    
    constraints = [

        models.UniqueConstraint(
            fields=[
                "staff",
                "attendance_date",
            ],
            name="unique_staff_attendance_per_day",
        ),

    ]
    
    indexes = [

        models.Index(fields=["restaurant"]),

        models.Index(fields=["staff"]),

        models.Index(fields=["attendance_date"]),

        models.Index(fields=["status"]),

        models.Index(fields=["is_deleted"]),

        models.Index(
            fields=[
                "restaurant",
                "attendance_date",
            ]
        ),

    ]
    
# =============================================================================
# Staff Shift Schedule
# =============================================================================

class StaffShiftSchedule(models.Model):
    """
    Weekly recurring shift schedule for a staff member.
    """

    DAYS_OF_WEEK = [

        ("monday", "Monday"),
        ("tuesday", "Tuesday"),
        ("wednesday", "Wednesday"),
        ("thursday", "Thursday"),
        ("friday", "Friday"),
        ("saturday", "Saturday"),
        ("sunday", "Sunday"),

    ]

    # ==========================================================
    # Relationships
    # ==========================================================

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="shift_schedules",
    )

    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name="shift_schedules",
    )

    # ==========================================================
    # Schedule
    # ==========================================================

    day_of_week = models.CharField(
        max_length=10,
        choices=DAYS_OF_WEEK,
    )

    shift_start = models.TimeField()

    shift_end = models.TimeField()

    is_off_day = models.BooleanField(
        
        default=False,
        
    )

    # ==========================================================
    # Status
    # ==========================================================

    is_active = models.BooleanField(
        default=True,
    )

    is_deleted = models.BooleanField(
        default=False,
    )

    # ==========================================================
    # Audit
    # ==========================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        ordering = [
            "staff",
            "day_of_week",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "staff",
                    "day_of_week",
                ],
                name="unique_shift_per_staff_per_day",
            ),

        ]

        indexes = [

            models.Index(fields=["restaurant"]),

            models.Index(fields=["staff"]),

            models.Index(fields=["day_of_week"]),

            models.Index(fields=["is_active"]),

            models.Index(fields=["is_deleted"]),

        ]

    def __str__(self):

        return (
            f"{self.staff.full_name} - "
            f"{self.get_day_of_week_display()}"
        )
             
# ==========================================================
# Staff Break
# ==========================================================

class StaffBreak(models.Model):
    """
    Staff break history.
    """

    attendance = models.ForeignKey(
        StaffAttendance,
        on_delete=models.CASCADE,
        related_name="breaks",
    )

    break_start = models.DateTimeField()

    break_end = models.DateTimeField(
        null=True,
        blank=True,
    )

    minutes = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        ordering = [
            "-break_start",
        ]

        indexes = [

            models.Index(fields=["attendance"]),

            models.Index(fields=["is_active"]),

        ]

    def __str__(self):

        return (
            f"{self.attendance.staff.full_name}"
            f" | Break"
        )
        
# =============================================================================
# Audit Log
# =============================================================================

class AuditLog(models.Model):
    """
    Stores an audit trail for important restaurant actions.
    """

    # ==========================================================
    # Actions
    # ==========================================================

    class Action(models.TextChoices):

        # -------------------------
        # Staff
        # -------------------------

        STAFF_CREATED = (
            "staff_created",
            "Staff Created",
        )

        STAFF_UPDATED = (
            "staff_updated",
            "Staff Updated",
        )

        STAFF_DELETED = (
            "staff_deleted",
            "Staff Deleted",
        )

        ROLE_CHANGED = (
            "role_changed",
            "Role Changed",
        )

        SHIFT_STARTED = (
            "shift_started",
            "Shift Started",
        )

        SHIFT_ENDED = (
            "shift_ended",
            "Shift Ended",
        )

        # -------------------------
        # Attendance
        # -------------------------

        CLOCK_IN = (
            "clock_in",
            "Clock In",
        )

        CLOCK_OUT = (
            "clock_out",
            "Clock Out",
        )

        BREAK_STARTED = (
            "break_started",
            "Break Started",
        )

        BREAK_ENDED = (
            "break_ended",
            "Break Ended",
        )

        # -------------------------
        # Kitchen
        # -------------------------

        KITCHEN_NOTE_CREATED = (
            "kitchen_note_created",
            "Kitchen Note Created",
        )

        KITCHEN_NOTE_UPDATED = (
            "kitchen_note_updated",
            "Kitchen Note Updated",
        )

        KITCHEN_NOTE_ARCHIVED = (
            "kitchen_note_archived",
            "Kitchen Note Archived",
        )

        ORDER_CONFIRMED = (
            "order_confirmed",
            "Order Confirmed",
        )

        ORDER_PREPARING = (
            "order_preparing",
            "Order Preparing",
        )

        ORDER_READY = (
            "order_ready",
            "Order Ready",
        )

        ORDER_SERVED = (
            "order_served",
            "Order Served",
        )

        PRIORITY_CHANGED = (
            "priority_changed",
            "Priority Changed",
        )

        # -------------------------
        # Delivery
        # -------------------------

        DELIVERY_ASSIGNED = (
            "delivery_assigned",
            "Delivery Assigned",
        )

        DELIVERY_STARTED = (
            "delivery_started",
            "Delivery Started",
        )

        DELIVERY_COMPLETED = (
            "delivery_completed",
            "Delivery Completed",
        )

        DELIVERY_CANCELLED = (
            "delivery_cancelled",
            "Delivery Cancelled",
        )

        # -------------------------
        # Restaurant
        # -------------------------

        RESTAURANT_UPDATED = (
            "restaurant_updated",
            "Restaurant Updated",
        )

        SETTINGS_UPDATED = (
            "settings_updated",
            "Settings Updated",
        )

        SUBSCRIPTION_CHANGED = (
            "subscription_changed",
            "Subscription Changed",
        )

        PAYMENT_RECEIVED = (
            "payment_received",
            "Payment Received",
        )

    # ==========================================================
    # Entities
    # ==========================================================

    class Entity(models.TextChoices):

        # -------------------------
        # Restaurant
        # -------------------------

        RESTAURANT = (
            "restaurant",
            "Restaurant",
        )

        # -------------------------
        # Staff
        # -------------------------

        STAFF = (
            "staff",
            "Staff",
        )

        STAFF_ATTENDANCE = (
            "staff_attendance",
            "Staff Attendance",
        )

        STAFF_BREAK = (
            "staff_break",
            "Staff Break",
        )

        STAFF_SHIFT_SCHEDULE = (
            "staff_shift_schedule",
            "Staff Shift Schedule",
        )

        # -------------------------
        # Orders
        # -------------------------

        ORDER = (
            "order",
            "Order",
        )

        ORDER_ITEM = (
            "order_item",
            "Order Item",
        )

        # -------------------------
        # Kitchen
        # -------------------------

        KITCHEN_NOTE = (
            "kitchen_note",
            "Kitchen Note",
        )

        # -------------------------
        # Menu
        # -------------------------

        CATEGORY = (
            "category",
            "Category",
        )

        FOOD_ITEM = (
            "food_item",
            "Food Item",
        )

        # -------------------------
        # Tables
        # -------------------------

        TABLE = (
            "table",
            "Table",
        )

        # -------------------------
        # Delivery
        # -------------------------

        DELIVERY = (
            "delivery",
            "Delivery",
        )

        DELIVERY_PARTNER = (
            "delivery_partner",
            "Delivery Partner",
        )

        # -------------------------
        # Dashboard
        # -------------------------

        DASHBOARD = (
            "dashboard",
            "Dashboard",
        )

        # -------------------------
        # Payments
        # -------------------------

        PAYMENT = (
            "payment",
            "Payment",
        )

        SUBSCRIPTION = (
            "subscription",
            "Subscription",
        )


    # ==========================================================
    # Relationships
    # ==========================================================
    
    request_id = models.CharField(
        max_length=100,
        blank=True,
    )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )

    staff = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="Staff member who performed the action.",
    )

    # ==========================================================
    # Audit Information
    # ==========================================================

    action = models.CharField(
        max_length=50,
        choices=Action.choices,
    )

    entity = models.CharField(
        max_length=50,
        choices=Entity.choices,
    )

    entity_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="Primary key of the affected entity.",
    )

    description = models.TextField()

    # ==========================================================
    # Request Metadata
    # ==========================================================

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    user_agent = models.TextField(
        blank=True,
    )

    # ==========================================================
    # Audit
    # ==========================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        ordering = [
            "-created_at",
        ]

        indexes = [

            models.Index(
                fields=[
                    "restaurant",
                ]
            ),

            models.Index(
                fields=[
                    "staff",
                ]
            ),

            models.Index(
                fields=[
                    "action",
                ]
            ),

            models.Index(
                fields=[
                    "entity",
                ]
            ),

            models.Index(
                fields=[
                    "entity_id",
                ]
            ),

            models.Index(
                fields=[
                    "created_at",
                ]
            ),

        ]

    def __str__(self):

        return (

            f"{self.restaurant.name}"

            f" | "

            f"{self.get_action_display()}"

            f" | "

            f"{self.entity}"

            f" ("

            f"{self.entity_id}"

            f")"

        )
        
        
        
