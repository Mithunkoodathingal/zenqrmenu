from django.contrib import admin
from django.utils.html import format_html
from .models import FoodItem, Category


class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'restaurant']
    list_filter = ['restaurant']


class FoodItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'image_preview', 'restaurant')
    list_filter = ['restaurant', 'category']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />'.format(obj.image.url))
        return "No Image"

    image_preview.short_description = 'Image'


admin.site.register(Category, CategoryAdmin)
admin.site.register(FoodItem, FoodItemAdmin)

