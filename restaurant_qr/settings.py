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

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_AGE = 60 * 60 * 24  # 1 day

# after DEBUG = config(...) line
# Force local sqlite for dev when DJANGO_DEBUG/DJANGO_ENV indicates debug mode
if DEBUG and not os.getenv("FORCE_POSTGRES", ""):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# Site
SITE_NAME = config('SITE_NAME', default='Zen Menu')
SITE_ID = config('SITE_ID', default=1, cast=int)

# Hosts (comma-separated in .env). In production set ALLOWED_HOSTS to your domain(s).
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='http://localhost:8000/', cast=Csv())  # e.g. "example.com,www.example.com"
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://zenqrmenu.onrender.com",
    "https://www.zenqrmenu.com",
    "https://zenqrmenu.com",
]



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
    'rest_framework',
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
    'storages',

    # sites (required by allauth)
    'django.contrib.sites',

    # local
    'restaurant.apps.RestaurantConfig',
    'corsheaders',
    'subscription',
    'payments',
]

# -------------------------
# Middleware
# -------------------------
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
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
# Database (PostgreSQL via DATABASE_URL or Cloud SQL socket)
# -------------------------
# Preferred order:
# 1) If CLOUD_SQL_INSTANCE is set (Cloud Run attached Cloud SQL), use unix socket
# 2) Else if DATABASE_URL provided, use dj_database_url
# 3) Else fall back to sqlite for local dev

CLOUD_SQL_INSTANCE = config('CLOUD_SQL_INSTANCE', default='').strip()
DB_NAME = config('DB_NAME', default='').strip()
DB_USER = config('DB_USER', default='').strip()
DB_PASS = config('DB_PASS', default='').strip()

DB_CONN_MAX_AGE = config(
    'DB_CONN_MAX_AGE',
    default=600,
    cast=int
)

DB_SSL_REQUIRE = config(
    'DB_SSL_REQUIRE',
    default=True,
    cast=bool
)

if CLOUD_SQL_INSTANCE and DB_NAME and DB_USER and DB_PASS:

    # Cloud SQL via unix socket
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': DB_NAME,
            'USER': DB_USER,
            'PASSWORD': DB_PASS,
            'HOST': os.path.join('/cloudsql', CLOUD_SQL_INSTANCE),
            'PORT': '',
            'CONN_MAX_AGE': DB_CONN_MAX_AGE,
            'CONN_HEALTH_CHECKS': True,
        }
    }

else:

    DATABASE_URL = config(
        'DATABASE_URL',
        default=''
    ).strip()

    if DATABASE_URL:

        try:
            import dj_database_url

            DATABASES = {
                'default': dj_database_url.parse(
                    DATABASE_URL,
                    conn_max_age=DB_CONN_MAX_AGE,
                    ssl_require=True,
                )
            }

            # Extra SSL stability for Neon/Render/Postgres
            DATABASES['default']['OPTIONS'] = {
                'sslmode': 'require',
            }

            # Better connection recovery
            DATABASES['default']['CONN_HEALTH_CHECKS'] = True

        except Exception:

            DATABASES = {
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': BASE_DIR / 'db.sqlite3',
                }
            }

    else:

        # Local development fallback
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
# NOTE: Do NOT set STATICFILES_STORAGE here when using the STORAGES dict below.

MEDIA_URL = config('MEDIA_URL', default='/media/')
MEDIA_ROOT = config('MEDIA_ROOT', default=os.path.join(BASE_DIR, 'media'))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# -----------------------------
# Cloudflare R2 — MEDIA ONLY
# -----------------------------

USE_S3 = True

AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")

AWS_S3_ENDPOINT_URL = config("AWS_S3_ENDPOINT_URL")
AWS_S3_CUSTOM_DOMAIN = config("AWS_S3_PUBLIC_URL")
AWS_S3_PUBLIC_URL = config("AWS_S3_PUBLIC_URL")
AWS_S3_REGION_NAME = "auto"
AWS_S3_ADDRESSING_STYLE = "path"

AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = False
AWS_S3_FILE_OVERWRITE = False

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "endpoint_url": AWS_S3_ENDPOINT_URL,
        },
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# 🔥 MEDIA ROOT IS BUCKET ROOT
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"

# Local static
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "restaurant" / "static"]





# USE_S3 = config("USE_S3", default=False, cast=bool)

# # Common defaults
# STATICFILES_LOCATION = config("STATICFILES_LOCATION", default="static")
# MEDIAFILES_LOCATION = config("MEDIAFILES_LOCATION", default="media")

# if USE_S3:
#     # --- S3 credentials and settings ---
#     AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
#     AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
#     AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")

#     AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME') or None
#     AWS_S3_CUSTOM_DOMAIN = config("AWS_S3_CUSTOM_DOMAIN", default="")  # optional
#     AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL') or None

#     AWS_DEFAULT_ACL = None
#     AWS_S3_FILE_OVERWRITE = config("AWS_S3_FILE_OVERWRITE", default=False, cast=bool)
#     AWS_QUERYSTRING_AUTH = False
#     AWS_S3_SIGNATURE_VERSION = config("AWS_S3_SIGNATURE_VERSION", default="s3v4")
#     AWS_S3_OBJECT_PARAMETERS = {}

#     # Backward-compatible OPTIONS
#     _default_options = {}
#     if AWS_S3_ENDPOINT_URL:
#         _default_options["endpoint_url"] = AWS_S3_ENDPOINT_URL

#     # --- Django 5 STORAGES mapping ---
#     STORAGES = {
#         "default": {
#             "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
#             "OPTIONS": _default_options,
#         },
#         "staticfiles": {
#             "BACKEND": "restaurant.storages.StaticS3Storage",
#             "OPTIONS": {"location": STATICFILES_LOCATION},
#         },
#         "media": {
#             "BACKEND": "restaurant.storages.MediaS3Storage",
#             "OPTIONS": {"location": MEDIAFILES_LOCATION},
#         },
#     }

#     # --- URLs for public access ---
#     if AWS_S3_CUSTOM_DOMAIN:
#         STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{STATICFILES_LOCATION}/"
#         MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{MEDIAFILES_LOCATION}/"
#     else:
#         if AWS_S3_ENDPOINT_URL:
#             STATIC_URL = f"{AWS_S3_ENDPOINT_URL.rstrip('/')}/{AWS_STORAGE_BUCKET_NAME}/{STATICFILES_LOCATION}/"
#             MEDIA_URL = f"{AWS_S3_ENDPOINT_URL.rstrip('/')}/{AWS_STORAGE_BUCKET_NAME}/{MEDIAFILES_LOCATION}/"
#         else:
#             STATIC_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{STATICFILES_LOCATION}/"
#             MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{MEDIAFILES_LOCATION}/"

# else:
#     # --- Local dev fallback ---
#     STATIC_URL = config("STATIC_URL", default="/static/")
#     STATIC_ROOT = config("STATIC_ROOT", default=os.path.join(BASE_DIR, "staticfiles"))
#     STATICFILES_DIRS = [BASE_DIR / "restaurant" / "static"]

#     MEDIA_URL = config("MEDIA_URL", default="/media/")
#     MEDIA_ROOT = config("MEDIA_ROOT", default=os.path.join(BASE_DIR, "media"))

#     STORAGES = {
#         "default": {
#             "BACKEND": "django.core.files.storage.FileSystemStorage",
#             "OPTIONS": {"location": MEDIA_ROOT},
#         },
#         "staticfiles": {
#             "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
#             "OPTIONS": {"location": STATIC_ROOT},
#         },
#     }

# ✅ REMOVE the following lines if present anywhere:
# DEFAULT_FILE_STORAGE = ...
# STATICFILES_STORAGE = ...



# -------------------------
# Sites / allauth / Email
# -------------------------
import os

INSTALLED_APPS += ["anymail"]

# ----- helper: sanitize DEFAULT_FROM_EMAIL from env (remove quotes/newlines/extra spaces)
def _clean_env_from_email(value, *, default="Zen QR Menu <hello@zenqrmenu.com>"):
    """
    Normalize DEFAULT_FROM_EMAIL loaded from environment:
    - return default if value is None or empty after cleaning
    - strip surrounding single/double quotes, whitespace and newlines
    - collapse internal newlines into spaces
    """
    if not value:
        return default
    # Trim whitespace, remove surrounding quotes, collapse newlines
    v = value.strip().strip('"').strip("'")
    v = " ".join(v.splitlines())  # collapse newlines
    v = v.strip()
    return v or default

# Anymail / Brevo config (use API via Anymail)
EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"

# Top-level compatibility keys (some anymail versions look here)
BREVO_API_KEY = config("BREVO_API_KEY")            # top-level key
ANYMAIL_BREVO_API_KEY = BREVO_API_KEY              # legacy name anymail may check

# Primary ANYMAIL dict (modern shape)


ANYMAIL = {
    "BREVO_API_KEY": BREVO_API_KEY,
}

# DEFAULT_FROM_EMAIL: read raw env and sanitize
# Use os.getenv to read the raw environment value so we can clean it safely.
_raw_default_from = os.getenv("DEFAULT_FROM_EMAIL") or ""
DEFAULT_FROM_EMAIL = _clean_env_from_email(_raw_default_from, default="Zen QR Menu <hello@zenqrmenu.com>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Timeout for email operations
EMAIL_TIMEOUT = int(config("EMAIL_TIMEOUT", default=5))

# Optional: If you're also providing SMTP fallback values in env, keep them,
# but with safe casting/parsing.
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
# support both boolean-like strings and proper bools from decouple
try:
    EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
except Exception:
    EMAIL_USE_TLS = str(os.getenv("EMAIL_USE_TLS", "True")).lower() in ("1", "true", "yes")

EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")

# Keep your allauth/account settings
ACCOUNT_ADAPTER = "restaurant.adapters.CustomAccountAdapter"
EMAIL_SUBJECT_PREFIX = ""
ACCOUNT_EMAIL_SUBJECT_PREFIX = ""

ACCOUNT_FORMS = {
    "signup": "restaurant.forms.SignupForm",
}



# allauth configuration
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = config('ACCOUNT_EMAIL_VERIFICATION', default='mandatory')
ACCOUNT_UNIQUE_EMAIL = config('ACCOUNT_UNIQUE_EMAIL', default=True, cast=bool)
ACCOUNT_LOGIN_METHODS = config('ACCOUNT_LOGIN_METHODS', default='username,email', cast=Csv())
ACCOUNT_CONFIRM_EMAIL_ON_GET = config('ACCOUNT_CONFIRM_EMAIL_ON_GET', default=False, cast=bool)
ACCOUNT_LOGIN_METHODS = {"email", "username"}

ACCOUNT_SIGNUP_FIELDS = [
    "email*",
    "username*",
    "password1*",
    "password2*"
]

# Auth backends
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Login/Logout
LOGIN_REDIRECT_URL = config('LOGIN_REDIRECT_URL', default='dashboard')
LOGOUT_REDIRECT_URL = config('LOGOUT_REDIRECT_URL', default="https://www.zenqrmenu.com/login")
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = "https://www.zenqrmenu.com/email-verified"
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = "https://www.zenqrmenu.com/email-verified"
ACCOUNT_CONFIRM_EMAIL_ON_GET = True

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

CSRF_TRUSTED_ORIGINS = [
    "https://zenqrmenu.com",
]

CORS_ALLOW_ALL_ORIGINS = True   # 🔥 TEMP DEBUG (enable this now)


from corsheaders.defaults import default_headers



CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = list(default_headers) + [
    "cache-control",
    "pragma",
]

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='',
    cast=Csv()
)

CORS_ALLOWED_ORIGINS = [
    "http://localhost:8080",
    "https://zenqrmenu.com",
    "https://api.zenqrmenu.com",
]


SESSION_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True

CSRF_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SECURE = True

# Optional: if you need file uploads to be served from a cloud storage (S3, etc.), configure here.

# -------------------------
# End of file
# -------------------------


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',   # Change to DEBUG for detailed info
    },
}


from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

PAYMENT_ENCRYPTION_KEY = os.getenv(
    "PAYMENT_ENCRYPTION_KEY"
)

BRAND_NAME = "ZenQRMenu"

BRAND_URL = "https://zenqrmenu.com"