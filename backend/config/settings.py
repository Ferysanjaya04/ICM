from pathlib import Path
import os
from urllib.parse import urlsplit

from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

# =========================================================
# BASE CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env dari root project:
# VitLog/.env
load_dotenv(BASE_DIR.parent / ".env")


# =========================================================
# SECURITY
# =========================================================

def env_bool(name, default=False):
    value = os.getenv(name, str(default)).strip().lower()
    if value not in {"true", "false", "1", "0"}:
        raise ImproperlyConfigured(f"{name} must be true/false or 1/0.")
    return value in {"true", "1"}


def env_list(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


DJANGO_ENV = os.getenv("DJANGO_ENV", "development").strip().lower()
if DJANGO_ENV not in {"development", "production"}:
    raise ImproperlyConfigured("DJANGO_ENV must be development or production.")
IS_PRODUCTION = DJANGO_ENV == "production"
DEBUG = env_bool("DEBUG", not IS_PRODUCTION)
if IS_PRODUCTION and DEBUG:
    raise ImproperlyConfigured("DEBUG must be false in production.")

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if IS_PRODUCTION and (
    len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5
    or SECRET_KEY.startswith("django-insecure-")
):
    raise ImproperlyConfigured("Production requires a strong SECRET_KEY from the environment.")
if not SECRET_KEY:
    # Local convenience only; set SECRET_KEY in .env to retain tokens across restarts.
    SECRET_KEY = get_random_secret_key()

ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS", "" if IS_PRODUCTION else "localhost,127.0.0.1,testserver"
)
if IS_PRODUCTION and (
    not ALLOWED_HOSTS or any("*" in host or "/" in host for host in ALLOWED_HOSTS)
):
    raise ImproperlyConfigured("Production requires explicit ALLOWED_HOSTS without wildcards.")

# Production is HTTPS-only. Development keeps localhost HTTP and non-secure cookies.
SECURE_SSL_REDIRECT = IS_PRODUCTION
SESSION_COOKIE_SECURE = IS_PRODUCTION
CSRF_COOKIE_SECURE = IS_PRODUCTION
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
try:
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "3600" if IS_PRODUCTION else "0"))
except ValueError as exc:
    raise ImproperlyConfigured("SECURE_HSTS_SECONDS must be an integer.") from exc
if SECURE_HSTS_SECONDS < 0 or (IS_PRODUCTION and SECURE_HSTS_SECONDS == 0):
    raise ImproperlyConfigured("Production requires positive SECURE_HSTS_SECONDS.")
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS")
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD")

# Enable ONLY behind a trusted proxy that strips/replaces client-supplied headers.
if env_bool("TRUST_PROXY_HTTPS"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# =========================================================
# APPLICATIONS
# =========================================================

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "corsheaders",

    # ICM Apps
    "accounts",
    "resumes",
    "analysis",
    "recommendations",
]


# =========================================================
# MIDDLEWARE
# =========================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    "corsheaders.middleware.CorsMiddleware",

    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# =========================================================
# URL / WSGI
# =========================================================

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"


# =========================================================
# TEMPLATES
# =========================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# =========================================================
# DATABASE - POSTGRESQL
# =========================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}


# =========================================================
# PASSWORD VALIDATION
# =========================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME":
        "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME":
        "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME":
        "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME":
        "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# =========================================================
# INTERNATIONALIZATION
# =========================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Jakarta"

USE_I18N = True

USE_TZ = True


# =========================================================
# STATIC FILES
# =========================================================

STATIC_URL = "static/"

STATICFILES_DIRS = []

STATIC_ROOT = BASE_DIR / "staticfiles"


# =========================================================
# DEFAULT PRIMARY KEY
# =========================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# =========================================================
# DJANGO REST FRAMEWORK
# =========================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}


# =========================================================
# CORS - REACT FRONTEND
# =========================================================

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "" if IS_PRODUCTION else "http://localhost:5500,http://127.0.0.1:5500",
)
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")
CORS_ALLOW_ALL_ORIGINS = False
for origin in CORS_ALLOWED_ORIGINS + CSRF_TRUSTED_ORIGINS:
    try:
        parsed = urlsplit(origin)
        parsed.port  # Reject malformed ports as well as malformed hosts.
        valid = (
            parsed.scheme in ({"https"} if IS_PRODUCTION else {"http", "https"})
            and parsed.hostname and "*" not in origin and not parsed.username
            and not parsed.password and not parsed.path and not parsed.query
            and not parsed.fragment
        )
    except ValueError:
        valid = False
    if not valid:
        raise ImproperlyConfigured("CORS/CSRF origins must be explicit origins; production requires HTTPS.")

# =========================================================
# LOGGING - FEATURE 1 / CV JOB MATCHING
# =========================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "verbose": {
            "format": (
                "{asctime} [{levelname}] {name}: {message}"
            ),
            "style": "{",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },

    "loggers": {
        # Log dari AnalysisService dan Feature 1
        "analysis": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },

        # Log error dari modul aplikasi lain tetap diteruskan
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

# =========================================================
# MEDIA FILES - CV UPLOAD
# =========================================================

# Legacy files are READ ONLY through private storage; never serve either root over HTTP.
MEDIA_URL = "/media/"
legacy_root = Path(os.getenv("LEGACY_RESUME_ROOT", str(BASE_DIR / "media"))).expanduser()
if not legacy_root.is_absolute():
    raise ImproperlyConfigured("LEGACY_RESUME_ROOT must be an absolute path.")
MEDIA_ROOT = legacy_root.resolve()
private_root = Path(os.getenv(
    "PRIVATE_RESUME_ROOT", str(BASE_DIR.parent.parent / "VitLog-private" / "media")
)).expanduser()
if not private_root.is_absolute():
    raise ImproperlyConfigured("PRIVATE_RESUME_ROOT must be an absolute path.")
PRIVATE_RESUME_ROOT = private_root.resolve()
if (
    PRIVATE_RESUME_ROOT.is_relative_to(MEDIA_ROOT)
    or MEDIA_ROOT.is_relative_to(PRIVATE_RESUME_ROOT)
    or any(
        root.is_relative_to(STATIC_ROOT.resolve()) or STATIC_ROOT.resolve().is_relative_to(root)
        for root in (PRIVATE_RESUME_ROOT, MEDIA_ROOT)
    )
    or (IS_PRODUCTION and PRIVATE_RESUME_ROOT.is_relative_to(BASE_DIR.parent.resolve()))
):
    raise ImproperlyConfigured("Private, legacy and static roots must be isolated; production private storage must be outside the project.")

STORAGES = {
    "default": {"BACKEND": "resumes.storage.PrivateResumeStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
