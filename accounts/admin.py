from django.contrib import admin

from .models import OwnerAccount


@admin.register(OwnerAccount)
class OwnerAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "email_verified", "verified_at", "created_at")
    list_filter = ("email_verified",)
    search_fields = ("user__username", "user__email")
