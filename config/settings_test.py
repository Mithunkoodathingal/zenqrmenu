"""Fast, isolated settings for the automated checks (SQLite in memory, emails captured)."""
import os

os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("SECRET_KEY", "test-secret")

from .settings import *  # noqa: E402,F401,F403

if not os.environ.get("TEST_DATABASE_URL"):
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
else:
    import dj_database_url
    DATABASES = {"default": dj_database_url.parse(os.environ["TEST_DATABASE_URL"])}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": {"auth": "1000/min", "otp": "1000/min", "public": "1000/min"}}
FRONTEND_URL = "http://frontend.test"
BACKEND_URL = "http://testserver"
