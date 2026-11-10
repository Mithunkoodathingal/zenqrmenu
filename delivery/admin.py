from django.contrib import admin

from .models import DeliveryAssignment, DeliveryPartner

admin.site.register(DeliveryPartner)
admin.site.register(DeliveryAssignment)
