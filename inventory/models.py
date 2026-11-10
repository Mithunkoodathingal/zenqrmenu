"""Ingredients, per-branch stock, purchases, the stock history and recipes.

Stock changes only through adjustments, purchases and order events, each writing a `StockMovement`,
so the history always explains the current number.
"""
from django.conf import settings
from django.db import models

from restaurants.models import Branch, Restaurant


class Ingredient(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="ingredients")
    name = models.CharField(max_length=120)
    unit = models.CharField(max_length=20)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sku = models.CharField(max_length=60, blank=True)
    low_stock_threshold = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class StockLevel(models.Model):
    """One ingredient at one branch. `reserved` is held for confirmed orders that aren't completed yet."""

    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="levels")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="stock_levels")
    on_hand = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    reserved = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["ingredient", "branch"], name="one_level_per_branch")]

    @property
    def available(self):
        return self.on_hand - self.reserved


class StockMovement(models.Model):
    class Kind(models.TextChoices):
        OPENING = "opening"
        ADJUSTMENT = "adjustment"
        PURCHASE = "purchase"
        RESERVE = "reserve"
        RELEASE = "release"
        DEDUCT = "deduct"

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="stock_movements")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.SET_NULL, null=True, related_name="movements")
    ingredient_name = models.CharField(max_length=120)
    unit = models.CharField(max_length=20, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="stock_movements")
    delta = models.DecimalField(max_digits=12, decimal_places=3, help_text="Change to on-hand stock")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    reason = models.CharField(max_length=20, blank=True)
    note = models.CharField(max_length=255, blank=True)
    user = models.CharField(max_length=150, blank=True)
    order = models.ForeignKey("orders.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="stock_movements")
    on_hand_after = models.DecimalField(max_digits=12, decimal_places=3)
    reserved_after = models.DecimalField(max_digits=12, decimal_places=3)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class Purchase(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="stock_purchases")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.SET_NULL, null=True, related_name="purchases")
    ingredient_name = models.CharField(max_length=120)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="stock_purchases")
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    supplier = models.CharField(max_length=120, blank=True)
    invoice_no = models.CharField(max_length=60, blank=True)
    purchased_at = models.DateTimeField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-purchased_at", "-id"]


class Recipe(models.Model):
    """What one portion of a dish uses. One recipe per menu item, shared by all branches."""

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="recipes")
    food_item = models.OneToOneField("menu.FoodItem", on_delete=models.CASCADE, related_name="recipe")
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)


class RecipeLine(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="lines")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.PROTECT, related_name="recipe_lines")
    quantity = models.DecimalField(max_digits=12, decimal_places=3)

    class Meta:
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["recipe", "ingredient"], name="ingredient_once_per_recipe")]


class StockReservation(models.Model):
    """Ingredients held for one order. `lines` is a snapshot, so later recipe edits never change it."""

    class State(models.TextChoices):
        RESERVED = "reserved"
        DEDUCTED = "deducted"
        RELEASED = "released"

    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="stock_reservation")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="stock_reservations")
    state = models.CharField(max_length=10, choices=State.choices)
    lines = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
