from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Platform moderation: tick "removed by admin" to take a review down everywhere."""
    list_display = ("restaurant", "customer_name", "rating", "is_published", "removed_by_admin", "created_at")
    list_filter = ("removed_by_admin", "is_published", "rating")
    search_fields = ("customer_name", "comment", "restaurant__name")
    readonly_fields = ("restaurant", "order", "customer", "customer_name", "rating", "comment", "created_at", "edited_at")
