"""
URL configuration for restaurant_qr project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.urls import path, include
from django.conf import settings
from restaurant.views import MySignupView, lo

urlpatterns = [
    path('admin/', admin.site.urls),

    path('accounts/login/', login_view, name='account_login'),     # covers templates that use allauth name
    path('accounts/logout/', CustomLogoutView.as_view(), name='account_logout'),


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