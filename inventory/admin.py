from django.contrib import admin

from .models import Ingredient, Purchase, Recipe, StockLevel, StockMovement, StockReservation

for m in (Ingredient, Purchase, Recipe, StockLevel, StockMovement, StockReservation):
    admin.site.register(m)
