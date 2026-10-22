
"""
Django settings for SmartPrintKiosk.
QR-Based Smart Document Printing and Automated Kiosk System.

This configuration supports:
1. Environment variables loaded from .env during local development.
2. Accounts, printing, payments, and dashboard applications.
3. PostgreSQL for production and SQLite for local development.
4. WhiteNoise static-file serving.
5. Render hostname and HTTPS/CSRF configuration.
6. Secure production defaults and SmartPrintKiosk settings.

IMPORTANT:
- Set DJANGO_SECRET_KEY and DJANGO_DEBUG on Render.
- Set DB_ENGINE=postgresql and all DB_* variables on Render.
- Never commit your .env file or production credentials.
"""

import os
from pathlib import Path
from decimal import Decimal
from dotenv import load_dotenv

# ---------------------------------------------------------
# 1. PROJECT PATHS AND ENVIRONMENT VARIABLES
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

# Loads .env for local development. Render variables are
# supplied through the Render dashboard.
load_dotenv(BASE_DIR / ".env")


# ---------------------------------------------------------
# 2. SECURITY SETTINGS
# ---------------------------------------------------------

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

# Do not use an insecure fallback secret in production.
if not SECRET_KEY:
    if os.getenv("RENDER") or os.getenv("RENDER_EXTERNAL_HOSTNAME"):
        raise RuntimeError(
            "DJANGO_SECRET_KEY must be configured in Render."
        )

    # Local development fallback only.
    SECRET_KEY = (
        "django-insecure-local-development-only-change-this-key"
    )

DEBUG = os.getenv("DJANGO_DEBUG", "True").strip().lower() in (
    "true",
    "1",
    "yes",
)

# Render sets RENDER_EXTERNAL_HOSTNAME for deployed services.
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")

allowed_hosts_raw = os.getenv(
    "DJANGO_ALLOWED_HOSTS",
    "127.0.0.1,localhost",
)

ALLOWED_HOSTS = [
    host.strip()
    for host in allowed_hosts_raw.split(",")
    if host.strip()
]

# Include the assigned Render hostname automatically.
if RENDER_EXTERNAL_HOSTNAME:
    if RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Trusted origins are full origins, including HTTPS.
CSRF_TRUSTED_ORIGINS = [
    f"https://{host}"
    for host in ALLOWED_HOSTS
    if host not in ("localhost", "127.0.0.1")
]

# Respect Render's HTTPS reverse proxy.
if os.getenv("RENDER") or RENDER_EXTERNAL_HOSTNAME:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Secure browser settings for production.
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_REFERRER_POLICY = "same-origin"


# ---------------------------------------------------------
# 3. INSTALLED APPLICATIONS
# ---------------------------------------------------------

INSTALLED_APPS = [
    # Django built-in applications
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # SmartPrintKiosk applications
    "accounts.apps.AccountsConfig",
    "printing.apps.PrintingConfig",
    "payments.apps.PaymentsConfig",
    "dashboard.apps.DashboardConfig",
]


# ---------------------------------------------------------
# 4. MIDDLEWARE
# ---------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # Serve collected static files in production.
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ---------------------------------------------------------
# 5. URLS, TEMPLATES, AND APPLICATION SERVERS
# ---------------------------------------------------------

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        # Project-level templates folder.
        "DIRS": [BASE_DIR / "templates"],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",

                # Global kiosk/shop information and rates.
                "printing.context_processors.kiosk_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ---------------------------------------------------------
# 6. DATABASE CONFIGURATION
# ---------------------------------------------------------

# Local development defaults to SQLite.
# Production on Render should set DB_ENGINE=postgresql.
DB_ENGINE_CHOICE = os.getenv("DB_ENGINE", "sqlite").strip().lower()

if DB_ENGINE_CHOICE == "postgresql":
    # Do not silently use default credentials in production.
    required_db_variables = [
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "DB_HOST",
    ]

    missing_db_variables = [
        variable
        for variable in required_db_variables
        if not os.getenv(variable)
    ]

    if missing_db_variables:
        raise RuntimeError(
            "Missing PostgreSQL environment variables: "
            + ", ".join(missing_db_variables)
        )

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["DB_NAME"],
            "USER": os.environ["DB_USER"],
            "PASSWORD": os.environ["DB_PASSWORD"],
            "HOST": os.environ["DB_HOST"],
            "PORT": os.getenv("DB_PORT", "5432"),

            # Reuse connections briefly.
            "CONN_MAX_AGE": 60,

            # Require TLS for the hosted database connection.
            # If your provider uses a different SSL setup,
            # follow its connection instructions.
            "OPTIONS": {
                "sslmode": os.getenv("DB_SSLMODE", "require"),
            },
        }
    }

elif DB_ENGINE_CHOICE == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

else:
    raise RuntimeError(
        "Unsupported DB_ENGINE. Set it to 'sqlite' or 'postgresql'."
    )


# ---------------------------------------------------------
# 7. PASSWORD VALIDATION AND LOGIN
# ---------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
        "OPTIONS": {"min_length": 6},
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "printing:home"
LOGOUT_REDIRECT_URL = "printing:home"


# ---------------------------------------------------------
# 8. LANGUAGE AND TIME ZONE
# ---------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"

USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------
# 9. STATIC AND MEDIA FILES
# ---------------------------------------------------------

STATIC_URL = "/static/"

# Source static files, such as static/css/style.css.
STATICFILES_DIRS = [BASE_DIR / "static"]

# collectstatic writes production assets here.
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    # Uploaded customer documents use the default filesystem.
    # For production, configure persistent/object storage separately.
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },

    # WhiteNoise serves collected static assets.
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------
# 10. SMARTPRINTKIOSK SETTINGS
# ---------------------------------------------------------

# Maximum document upload size.
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "15"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Permitted document extensions.
ALLOWED_DOCUMENT_EXTENSIONS = [
    ".pdf",
    ".doc",
    ".docx",
    ".jpg",
    ".jpeg",
    ".png",
]

# Safe default: simulated printing.
PRINT_MODE = os.getenv("PRINT_MODE", "simulation").strip().lower()

# Default printing rates in Indian rupees.
DEFAULT_BW_RATE = Decimal(
    os.getenv("DEFAULT_BW_RATE", "2.00")
)

DEFAULT_COLOR_RATE = Decimal(
    os.getenv("DEFAULT_COLOR_RATE", "10.00")
)

DEFAULT_DUPLEX_DISCOUNT = Decimal(
    os.getenv("DEFAULT_DUPLEX_DISCOUNT", "0.00")
)
