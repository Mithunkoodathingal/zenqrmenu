from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from common.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health),
    path("", include("accounts.urls")),
    path("", include("restaurants.urls")),
    path("", include("menu.urls")),
    path("", include("subscriptions.urls")),
    path("", include("customers.urls")),
    path("", include("coupons.urls")),
    path("", include("orders.urls")),
    path("", include("payments.urls")),
    path("", include("inventory.urls")),
    path("", include("staff.urls")),
    path("", include("delivery.urls")),
    path("", include("kitchen.urls")),
    path("", include("notifications.urls")),
    path("", include("reviews.urls")),
    path("", include("marketing.urls")),
    path("", include("analytics.urls")),
]

if settings.DEBUG or not getattr(settings, "AWS_STORAGE_BUCKET_NAME", None):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
