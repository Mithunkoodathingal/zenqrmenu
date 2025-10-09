"""
Django settings for restaurant_qr project.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------- Basic ----------
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-$(58h=4%u99f0_dmen1k(o5kw8!-2^j-3a=h-7&%tdnhr@$7ze')
DEBUG = True

ALLOWED_HOSTS = [
    '.ngrok-free.app',
    'localhost',
    '127.0.0.1',
]

CSRF_TRUSTED_ORIGINS = [
    'https://*.ngrok-free.app'
]

# ---------- Apps ----------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # third-party
    "widget_tweaks",
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',

    # sites framework
    'django.contrib.sites',

    # your apps
    'restaurant',
    'subscription',
]

# ---------- Middleware ----------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # allauth account middleware (if installed)
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'restaurant_qr.urls'

# ---------- Templates ----------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # add a top-level templates dir if you use one
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',  # required by allauth
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # custom context processor to supply has_subscription & providers
                'restaurant.context_processors.global_template_vars',
            ],
        },
    },
]

WSGI_APPLICATION = 'restaurant_qr.wsgi.application'

# ---------- Database ----------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ---------- Password validation ----------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# ---------- Internationalization ----------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ---------- Static & Media ----------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "restaurant" / "static"]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------- Sites / Allauth / Email ----------
SITE_ID = 1

# Using your existing credentials (local dev). For production: move to env vars.
# NOTE: You previously had EMAIL_BACKEND = smtp with Gmail details. For development
# it is safer to use console backend. However you requested use of existing creds,
# so I'll configure SMTP using the credentials you provided.
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'            # corrected host
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'mithun.gfx@gmail.com'
EMAIL_HOST_PASSWORD = 'anuraz1986'       # <-- YOUR PROVIDED PASSWORD
DEFAULT_FROM_EMAIL = 'mithun.gfx@gmail.com'

# allauth: require email verification
# Using newer keys for clarity
ACCOUNT_SIGNUP_FIELDS = [
    'email*',
    'username*',
    'password1*',
    'password2*',
]
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'   # require confirmation before login
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGIN_METHODS = {'username', 'email'}
ACCOUNT_CONFIRM_EMAIL_ON_GET = False

# ---------- Authentication backends ----------
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # keep admin login working
    'allauth.account.auth_backends.AuthenticationBackend',
)

# ---------- Redirects ----------
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# ---------- Third-party keys (Razorpay) ----------
RAZORPAY_KEY_ID = 'rzp_test_LxyqCrk24R64s1'
RAZORPAY_KEY_SECRET = 'N6UfEYBIALtOogMrBdoiX98s'

# ---------- Development cookie settings ----------
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# ---------- Logging (basic) ----------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
}

