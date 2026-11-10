from django.contrib import admin

from .models import Notification, NotificationPreferences

admin.site.register(Notification)
admin.site.register(NotificationPreferences)
