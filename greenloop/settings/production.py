import os
from .base import *

DEBUG = False

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

# Database — Render injects DATABASE_URL automatically
import dj_database_url
db_from_env = dj_database_url.config(conn_max_age=600)
# Use PostGIS engine if DATABASE_URL is a postgres URL
if db_from_env:
    db_from_env["ENGINE"] = "django.contrib.gis.db.backends.postgis"
    DATABASES = {"default": db_from_env}
elif os.getenv("RENDER"):
    # On Render, if DATABASE_URL is missing, we must avoid SQLite fallback
    # which uses Path objects (causing TypeError: PosixPath has no len)
    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": "postgres",  # Placeholder to avoid TypeError
        }
    }

# Celery - read from environment
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

# Security
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = False  # Render handles SSL termination

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
