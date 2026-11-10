from django.contrib import admin

from .models import AddOn, Category, FoodItem


class AddOnInline(admin.TabularInline):
    model = AddOn
    extra = 0


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ("name", "restaurant", "category", "price", "original_price", "is_available")
    list_filter = ("is_available", "is_veg")
    search_fields = ("name", "restaurant__name")
    inlines = [AddOnInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "restaurant", "position")
    search_fields = ("name", "restaurant__name")
