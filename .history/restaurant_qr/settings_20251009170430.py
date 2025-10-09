"""
Django settings for restaurant_qr project.

Loading secrets from .env via python-decouple.
Production-minded defaults (DEBUG False, HSTS, secure cookies).
"""

import os
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# -------------------------
# Core / security settings
# -------------------------
SECRET_KEY = config('DJANGO_SECRET_KEY', default='django-insecure-placeholder-change-me')
DEBUG = config('DJANGO_DEBUG', default=False, cast=bool)

# Site
SITE_NAME = config('SITE_NAME', default='Zen Menu')
SITE_ID = config('SITE_ID', default=1, cast=int)

# Hosts (comma-separated in .env). In production set ALLOWED_HOSTS to your domain(s).
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='http://localhost:8000/', cast=Csv())  # e.g. "example.com,www.example.com"

# When behind a reverse proxy (Heroku, AWS ALB, etc.), enable:
USE_X_FORWARDED_HOST = config('USE_X_FORWARDED_HOST', default=False, cast=bool)
if USE_X_FORWARDED_HOST:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Trusted origins for CSRF (comma-separated), used for secure cookie handling + POSTs from frontends.
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# -------------------------
# Sentry (optional)
# -------------------------
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=float(config('SENTRY_TRACES_SAMPLE_RATE', default=0.05)),
        send_default_pii=True,
        environment=config('ENVIRONMENT', default='production'),
    )

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

    # third-party
    'widget_tweaks',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',

    # sites (required by allauth)
    'django.contrib.sites',

    # local
    'restaurant.apps.RestaurantConfig',
    'subscription',
]

# -------------------------
# Middleware
# -------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise should live right after SecurityMiddleware for static file serving.
    "whitenoise.middleware.WhiteNoiseMiddleware",

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware',
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
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',  # required by allauth
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'restaurant.context_processors.global_template_vars',
            ],
        },
    },
]

WSGI_APPLICATION = 'restaurant_qr.wsgi.application'

# -------------------------
# Database (PostgreSQL via DATABASE_URL)
# -------------------------
# Set DATABASE_URL in your .env, e.g.:
# DATABASE_URL=postgres://username:password@hostname:5432/dbname
DATABASE_URL = config('DATABASE_URL', default='').strip()
if DATABASE_URL:
    try:
        import dj_database_url

        DATABASES = {
            'default': dj_database_url.parse(
                DATABASE_URL,
                conn_max_age=config('DB_CONN_MAX_AGE', default=600, cast=int),
                ssl_require=config('DB_SSL_REQUIRE', default=True, cast=bool),
            )
        }
    except Exception:
        # Fallback safe sqlite (shouldn't be used in production)
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
else:
    # local/development fallback
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# -------------------------
# Password validators
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
# Static & media (WhiteNoise + collectstatic)
# -------------------------
STATIC_URL = config('STATIC_URL', default='/static/')
STATIC_ROOT = config('STATIC_ROOT', default=os.path.join(BASE_DIR, 'staticfiles'))
STATICFILES_DIRS = [BASE_DIR / "restaurant" / "static"]
STATICFILES_STORAGE = config('STATICFILES_STORAGE',
                             default='whitenoise.storage.CompressedManifestStaticFilesStorage')

MEDIA_URL = config('MEDIA_URL', default='/media/')
MEDIA_ROOT = config('MEDIA_ROOT', default=os.path.join(BASE_DIR, 'media'))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -------------------------
# Sites / allauth / Email
# -------------------------
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Zebra Menu <no-reply@localhost>')

EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

ACCOUNT_ADAPTER = 'restaurant.adapters.NoPrefixAccountAdapter'
EMAIL_SUBJECT_PREFIX = ''
ACCOUNT_EMAIL_SUBJECT_PREFIX = ''

ACCOUNT_FORMS = {
    'signup': 'restaurant.forms.SignupForm',
}

# allauth configuration
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = config('ACCOUNT_EMAIL_VERIFICATION', default='mandatory')
ACCOUNT_UNIQUE_EMAIL = config('ACCOUNT_UNIQUE_EMAIL', default=True, cast=bool)
ACCOUNT_LOGIN_METHODS = config('ACCOUNT_LOGIN_METHODS', default='username,email', cast=Csv())
ACCOUNT_CONFIRM_EMAIL_ON_GET = config('ACCOUNT_CONFIRM_EMAIL_ON_GET', default=False, cast=bool)

# Auth backends
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

# Login/Logout
LOGIN_REDIRECT_URL = config('LOGIN_REDIRECT_URL', default='dashboard')
LOGOUT_REDIRECT_URL = config('LOGOUT_REDIRECT_URL', default='login')

# Third party credentials
RAZORPAY_KEY_ID = config('RAZORPAY_KEY_ID', default='')
RAZORPAY_KEY_SECRET = config('RAZORPAY_KEY_SECRET', default='')

# -------------------------
# Security related flags (production defaults)
# -------------------------
# Encourage HTTPS in production. You can override via .env
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=not DEBUG, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=(not DEBUG), cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=(not DEBUG), cast=bool)

# HSTS - set to a reasonable default. If enabling, ensure SSL is fully working.
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=True, cast=bool)

# Prevent content type sniffing and enable XSS filter
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# -------------------------
# Logging (single robust config)
# -------------------------
# Uses python-json-logger if installed; falls back to simple console logging.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
        "simple": {"format": "%(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console_json": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
        "console_simple": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console_json"],
        "level": config('LOG_LEVEL', default='INFO'),
    },
    "loggers": {
        "django": {"handlers": ["console_json"], "level": config('DJANGO_LOG_LEVEL', default='INFO'), "propagate": False},
        "restaurant": {"handlers": ["console_json"], "level": config('APP_LOG_LEVEL', default='DEBUG'), "propagate": False},
    },
}

# -------------------------
# Misc
# -------------------------
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# Optional: if you need file uploads to be served from a cloud storage (S3, etc.), configure here.

# -------------------------
# End of file
# -------------------------
