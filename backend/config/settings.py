"""Django settings for the trip_app backend.

12-factor configuration via environment variables (see .env.example).
"""
import sys
from pathlib import Path

import dj_database_url
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CSRF_TRUSTED_ORIGINS=(list, []),
)
# Read a .env file if present (local dev). In prod, real env vars take precedence.
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    # Local
    "accounts",
    "trips",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": dj_database_url.parse(
        env("DATABASE_URL", default="postgres://trip:trip@localhost:5432/trip_app"),
        conn_max_age=600,
        # Neon free tier scales to zero when idle; health checks make Django
        # reconnect on a dropped connection instead of erroring after a wake-up.
        conn_health_checks=True,
    )
}

# Safety net: never run the test suite against the configured database (which
# may point at production). `manage.py test` always uses a local Postgres,
# overridable with TEST_DATABASE_URL.
if "test" in sys.argv:
    DATABASES["default"] = dj_database_url.parse(
        env("TEST_DATABASE_URL", default="postgres://trip:trip@localhost:5432/trip_app")
    )

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files. WhiteNoise serves these in production; it also serves the built
# Vue SPA (collected into STATIC_ROOT) so the API and frontend share one origin.
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# In production the compiled Vue SPA is copied to backend/spa/ (see Dockerfile).
# WhiteNoise serves its assets at the site root so the API and frontend are one
# origin. Guarded so local dev (which uses the Vite dev server) doesn't need it.
SPA_DIR = BASE_DIR / "spa"
if SPA_DIR.exists():
    WHITENOISE_ROOT = SPA_DIR
    WHITENOISE_INDEX_FILE = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # Applied only to views that opt in via throttle_scope (login / register).
    "DEFAULT_THROTTLE_RATES": {
        "login": "10/min",
        "register": "20/hour",
    },
}

# --- Session / CSRF cookies ---------------------------------------------------
# Same-origin SPA: the browser holds an httpOnly session cookie and a readable
# csrftoken cookie that the frontend echoes back in the X-CSRFToken header.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
# CSRF cookie must be readable by JS so axios can echo it back.
CSRF_COOKIE_HTTPONLY = False

if not DEBUG:
    # Behind Fly.io's TLS-terminating proxy.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    # Trust exactly one proxy (Fly.io) when identifying the client IP for
    # throttling, so the limiter keys on the real client, not a spoofable header.
    REST_FRAMEWORK["NUM_PROXIES"] = 1
