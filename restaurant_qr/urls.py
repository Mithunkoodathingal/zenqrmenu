# ----------- RESTAURANT_QR/URLS.PY ----------------------

from django.contrib import admin
from django.conf.urls.static import static

from django.urls import path, include
from django.conf import settings

# from restaurant.views import MySignupView, login_view, CustomLogoutView, signup_thankyou

# from django.views.generic import TemplateView


urlpatterns = [
    path('admin/', admin.site.urls),
    
    
    
    
    
    
    
    
# -----------------------------------------------------------------------------
# ---------------------- \/ OLD AND UNUSED API PATHS \/ -----------------------
# -----------------------------------------------------------------------------

    # path('accounts/login/', login_view, name='account_login'), 
    # path('login/', login_view, name='login'),    # covers templates that use allauth name
    # path('accounts/logout/', CustomLogoutView.as_view(), name='account_logout'),

    # # 1) Override the signup route BEFORE including allauth.
    # path('accounts/signup/', MySignupView.as_view(), name='account_signup'),

    # path('accounts/signup/thankyou/', signup_thankyou, name='signup_thankyou'),
    
# -----------------------------------------------------------------------------
# ---------------------- ^ OLD AND UNUSED API PATHS ^ -------------------------
# -----------------------------------------------------------------------------








    # 3) Now include the rest of allauth's URLs
    path('accounts/', include('allauth.urls')),

    # 4) Your app routes (example - adjust if your project root differs)
    path('', include('restaurant.urls')),   # ensure you have this file
    
    path('subscription/', include(('subscription.urls', 'subscription'), namespace='subscription')),
    
    path("payments/", include("payments.urls"),),
]

# Serve media files in development mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
