from django.urls import path

from . import views

urlpatterns = [
    path("api/register/", views.register),
    path("api/verify-email/", views.verify_email),
    path("api/resend-verification/", views.resend_verification),
    path("api/login/", views.login),
    path("api/logout/", views.logout),
    path("api/auth/refresh/", views.refresh),
    path("api/token/refresh/", views.refresh),
    path("api/auth/user/", views.current_user),
    path("api/user/", views.current_user),
    path("api/auth/google/", views.google),
    path("api/password/reset/", views.password_reset),
    path("api/password/reset/confirm/", views.password_reset_confirm),
]
