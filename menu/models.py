from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from restaurants.models import Branch, Restaurant


class Category(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=100)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]
        verbose_name_plural = "categories"
        constraints = [models.UniqueConstraint(fields=["restaurant", "name"], name="unique_category_name")]

    def __str__(self):
        return self.name


class FoodItem(models.Model):
    """`price` is what the diner pays. `original_price` is an optional higher "was" price shown struck through."""

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="items")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_available = models.BooleanField(default=True)
    is_veg = models.BooleanField(default=True)
    image = models.ImageField(upload_to="menu/items/", blank=True, null=True)
    image_url = models.URLField(blank=True, max_length=600)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category__position", "position", "id"]

    def __str__(self):
        return self.name


class AddOn(models.Model):
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE, related_name="addons")
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(Decimal("0"))])
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class BranchItemOverride(models.Model):
    """Per-branch tweaks to the shared menu: hide an item, or charge a different price."""

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="item_overrides")
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE, related_name="branch_overrides")
    is_available = models.BooleanField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["branch", "food_item"], name="unique_item_override")]


class BranchCategoryOverride(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="category_overrides")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="branch_overrides")
    is_available = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["branch", "category"], name="unique_category_override")]
