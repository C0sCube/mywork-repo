"""Django settings for the rep_fsparse web UI.

The existing parser/domain package in the repository remains the source of truth.
This project only replaces the Flask HTTP/UI layer.
"""
from pathlib import Path
import json
import os

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = Path(os.environ.get("REPO_FS_ROOT", BASE_DIR)).resolve()

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "change-me-in-production")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ['NCOG-LPT-TCH-32.Cogencis.com', 'localhost', '127.0.0.1']


# DEFAULT_HOST = "NCOG-LPT-TCH-32.Cogencis.com"
# DEFAULT_PORT = 5000


INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "webapp",
    "django_extensions"
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]

ROOT_URLCONF = "rep_fsparse_web.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "webapp" / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
    ]},
}]
WSGI_APPLICATION = "rep_fsparse_web.wsgi.application"
ASGI_APPLICATION = "rep_fsparse_web.asgi.application"

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "django.sqlite3"}}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "webapp" / "static"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SESSION_COOKIE_AGE = 7 * 24 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# The parser's existing paths.json remains external configuration.
PATHS_CONFIG = REPO_ROOT / "paths.json"
PATHS = {}
if PATHS_CONFIG.exists():
    try:
        PATHS = json.loads(PATHS_CONFIG.read_text(encoding="utf-8"))
    except Exception:
        PATHS = {}
