from django.contrib import admin

from .models import Branch, Restaurant, Table


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "city", "phone", "email", "is_active", "created_at")
    list_filter = ("is_active", "enable_delivery", "enable_pickup")
    search_fields = ("name", "owner__username", "owner__email", "email", "phone")
    inlines = [BranchInline]


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ("table_number", "restaurant", "branch")
    search_fields = ("restaurant__name", "table_number")
