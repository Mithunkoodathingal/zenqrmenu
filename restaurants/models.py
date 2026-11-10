from django.conf import settings
from django.db import models, transaction
from django.utils.text import slugify

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def default_hours():
    """Stored in the server shape the website converts from: monday/is_open/open/close + holidays."""
    hours = {d: {"is_open": True, "open": "09:00", "close": "22:00"} for d in DAYS}
    hours["holidays"] = []
    return hours


class Restaurant(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="restaurants")
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    about = models.TextField(blank=True)
    cuisines = models.JSONField(default=list, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    google_business_url = models.URLField(max_length=1000, blank=True, null=True)
    logo = models.ImageField(upload_to="restaurants/logos/", blank=True, null=True)
    cover_image = models.ImageField(upload_to="restaurants/covers/", blank=True, null=True)

    # Location (shown on the map, used for distance and delivery charges)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=80, blank=True)
    country = models.CharField(max_length=80, blank=True, default="India")
    pincode = models.CharField(max_length=12, blank=True)
    phone_country_code = models.CharField(max_length=6, blank=True, default="+91")

    # Pickup & delivery
    enable_delivery = models.BooleanField(default=False)
    enable_pickup = models.BooleanField(default=True)
    enable_dinein_payment = models.BooleanField(default=True)
    catering_available = models.BooleanField(default=False)
    max_delivery_km = models.DecimalField(max_digits=6, decimal_places=2, default=5)
    free_delivery_km = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    charge_per_extra_km = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    minimum_delivery_order = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    average_prep_minutes = models.PositiveIntegerField(default=20)

    working_hours = models.JSONField(default=default_hours, blank=True)
    settings = models.JSONField(default=dict, blank=True)
    currency = models.CharField(max_length=3, default="INR")

    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        creating = self.pk is None
        if not self.slug:
            base = slugify(self.name)[:150] or "restaurant"
            slug, n = base, 1
            while Restaurant.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
        with transaction.atomic():
            super().save(*args, **kwargs)
            if creating:
                Branch.objects.create(restaurant=self, name="Main branch", address=self.address, city=self.city,
                                      phone=self.phone, is_main=True)

    def main_branch(self):
        branch = self.branches.filter(is_main=True).first()
        if branch is None:
            branch = Branch.objects.create(restaurant=self, name="Main branch", address=self.address, phone=self.phone, is_main=True)
        return branch


class Branch(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=120)
    city = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_main = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_main", "id"]
        constraints = [
            models.UniqueConstraint(fields=["restaurant", "name"], name="unique_branch_name"),
            models.UniqueConstraint(fields=["restaurant"], condition=models.Q(is_main=True), name="one_main_branch"),
        ]

    def __str__(self):
        return f"{self.restaurant.name} — {self.name}"


class Table(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="tables")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="tables")
    table_number = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["restaurant", "table_number"], name="unique_table_number")]

    def __str__(self):
        return f"Table {self.table_number}"
