from django.contrib import admin

from .models import CustomerAddress, CustomerProfile


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "phone", "email_verified", "marketing_opt_in", "created_at")
    search_fields = ("email", "name", "phone")
    readonly_fields = ("unsubscribe_token", "marketing_consent_at", "unsubscribed_at")


@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    list_display = ("customer", "label", "city", "is_default")
    search_fields = ("customer__email", "city")
