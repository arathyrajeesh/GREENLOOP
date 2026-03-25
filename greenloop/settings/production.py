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

# Celery - read from environment
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

# Security
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = False  # Render handles SSL termination
