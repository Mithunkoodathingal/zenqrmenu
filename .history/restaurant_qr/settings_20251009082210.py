"""
Django settings for restaurant_qr project, loading secrets from .env via python-decouple.
"""

import os
from pathlib import Path
from decouple import config, Csv

# Base dir
BASE_DIR = Path(__file__).resolve().parent.parent

# -------------------------
# Core settings (from .env)
# -------------------------
SECRET_KEY = config('DJANGO_SECRET_KEY', default='django-insecure-placeholder-change-me')
DEBUG = config('DJANGO_DEBUG', default='True', cast=bool)
SITE_NAME = 'Zen Menu'

# hosts can be provided comma-separated in .env
# settings.py (development/test)
ALLOWED_HOSTS = ["*"]

# ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# -------------------------
# Installed apps
# -------------------------
INSTALLED_APPS = [
    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'widget_tweaks',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',

    # Sites (required by allauth)
    'django.contrib.sites',

    # Local apps
    'restaurant.apps.RestaurantConfig',
    'subscription',
]

# -------------------------
# Middleware
# -------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # allauth account middleware (optional for some setups)
    'allauth.account.middleware.AccountMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'restaurant_qr.urls'

# -------------------------
# Templates
# -------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Add your top-level templates dir if you have one
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',  # required by allauth
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                # optional: provide has_subscription/social providers
                'restaurant.context_processors.global_template_vars',
            ],
        },
    },
]



WSGI_APPLICATION = 'restaurant_qr.wsgi.application'

# -------------------------
# Database
# -------------------------
# Default: sqlite. To use DATABASE_URL (Postgres), set DATABASE_URL in .env and install dj-database-url.
if config('DATABASE_URL', default='').strip():
    # Optionally use dj-database-url if provided
    try:
        import dj_database_url
        DATABASES = {
            'default': dj_database_url.parse(config('DATABASE_URL'))
        }
    except Exception:
        # fallback to sqlite if dj-database-url not installed
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# -------------------------
# Password validation
# -------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# -------------------------
# Internationalization & timezone
# -------------------------
LANGUAGE_CODE = config('LANGUAGE_CODE', default='en-us')
TIME_ZONE = config('TIME_ZONE', default='Asia/Kolkata')
USE_I18N = True
USE_TZ = True

# -------------------------
# Static & media
# -------------------------
STATIC_URL = config('STATIC_URL', default='static/')
STATICFILES_DIRS = [BASE_DIR / "restaurant" / "static"]

MEDIA_URL = config('MEDIA_URL', default='/media/')
MEDIA_ROOT = config('MEDIA_ROOT', default=os.path.join(BASE_DIR, 'media'))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -------------------------
# Sites / Allauth / Email (from .env)
# -------------------------
SITE_ID = config('SITE_ID', default=1, cast=int)


if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    # Email settings (support console or SMTP)
    EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Zebra Menu <no-reply@localhost>')

    # SMTP fields (used only if EMAIL_BACKEND is smtp)
    EMAIL_HOST = config('EMAIL_HOST', default='')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')


EMAIL_SUBJECT_PREFIX = ''
# Tell allauth to use your custom signup form
ACCOUNT_FORMS = {
    'signup': 'restaurant.forms.SignupForm',
}


# -------------------------
# allauth configuration
# -------------------------
ACCOUNT_SIGNUP_FIELDS = [
    'email*',
    'username*',
    'password1*',
    'password2*',
]

# email verification behaviour: "mandatory", "optional", "none"
ACCOUNT_EMAIL_VERIFICATION = config('ACCOUNT_EMAIL_VERIFICATION', default='mandatory')
ACCOUNT_UNIQUE_EMAIL = config('ACCOUNT_UNIQUE_EMAIL', default=True, cast=bool)
ACCOUNT_LOGIN_METHODS = config('ACCOUNT_LOGIN_METHODS', default='username,email', cast=Csv())
ACCOUNT_CONFIRM_EMAIL_ON_GET = config('ACCOUNT_CONFIRM_EMAIL_ON_GET', default=False, cast=bool)
ACCOUNT_EMAIL_REQUIRED = True

# -------------------------
# Authentication backends
# -------------------------
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # admin login
    'allauth.account.auth_backends.AuthenticationBackend',  # allauth
)

# -------------------------
# Login/Logout
# -------------------------
LOGIN_REDIRECT_URL = config('LOGIN_REDIRECT_URL', default='dashboard')
LOGOUT_REDIRECT_URL = config('LOGOUT_REDIRECT_URL', default='login')

# -------------------------
# Third-party credentials (from .env)
# -------------------------
RAZORPAY_KEY_ID = config('RAZORPAY_KEY_ID', default='')
RAZORPAY_KEY_SECRET = config('RAZORPAY_KEY_SECRET', default='')

# -------------------------
# Session & security (dev defaults)
# -------------------------
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)

# -------------------------
# Logging (simple)
# -------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
