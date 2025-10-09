# restaurant_rq/urls.py  <-- save this as restaurant_qr/urls.py (overwrite current)
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

# Import the custom signup view you created
from restaurant.views_account import MySignupView

urlpatterns = [
    path('admin/', admin.site.urls),

    # 1) Override the signup route BEFORE including allauth.
    path('accounts/signup/', MySignupView.as_view(), name='account_signup'),

    # 2) friendly thank-you page
    path('accounts/signup/thankyou/', TemplateView.as_view(template_name='account/signup_thankyou.html'),
         name='signup_thankyou'),

    # 3) Now include the rest of allauth's URLs
    path('accounts/', include('allauth.urls')),

    # 4) Your app routes (example - adjust if your project root differs)
    path('', include('restaurant.urls')),   # ensure you have this file
    path('subscription/', include('subscription.urls')),  # if present
]


# Serve media files in development mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    
# 