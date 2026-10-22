"""
Django settings for SmartPrintKiosk project.
============================================
QR-Based Smart Document Printing and Automated Kiosk System

This module configures the entire Django application:
1. Environment variables loaded from .env
2. Installed apps (accounts, printing, payments, dashboard)
3. Database configuration (PostgreSQL target with SQLite fallback for offline setup)
4. Static & Media file routing
5. Security & Session settings
6. SmartPrint specific constants (upload limit, print rates, simulation mode)
"""

import os
from pathlib import Path
from decimal import Decimal
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file located at the project root
load_dotenv(BASE_DIR / '.env')

# ==============================================================================
# 1. CORE SECURITY & ENVIRONMENT SETTINGS
# ==============================================================================
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    'DJANGO_SECRET_KEY',
    'django-insecure-smartprint-kiosk-college-demo-default-secret-key-2026'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

# Allowed hosts: comma-separated in .env, defaults to localhost
allowed_hosts_raw = os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost')
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_raw.split(',') if host.strip()]


# ==============================================================================
# 2. APPLICATION DEFINITIONS
# ==============================================================================
INSTALLED_APPS = [
    # Core Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Custom SmartPrintKiosk apps
    'accounts.apps.AccountsConfig',      # User authentication, staff roles, profiles
    'printing.apps.PrintingConfig',      # Uploads, print options, orders, print queue
    'payments.apps.PaymentsConfig',      # Demo payments, verification, transaction ledger
    'dashboard.apps.DashboardConfig',    # Shop-owner control panel, stats, settings
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Look in the project-level templates folder
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Custom context processor for global kiosk shop info & rates
                'printing.context_processors.kiosk_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'


# ==============================================================================
# 3. DATABASE CONFIGURATION (PostgreSQL with SQLite Development Option)
# ==============================================================================
# As requested, PostgreSQL is the primary target database.
# DB_ENGINE can be set to 'postgresql' or 'sqlite' in the .env file.
# While PostgreSQL installation/configuration is pending on the user machine,
# 'sqlite' allows building, testing, and verifying the entire application.
DB_ENGINE_CHOICE = os.getenv('DB_ENGINE', 'sqlite').strip().lower()

if DB_ENGINE_CHOICE == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'smartprint_db'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }
else:
    # SQLite fallback for offline development/isolated testing
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# ==============================================================================
# 4. PASSWORD VALIDATION & AUTHENTICATION
# ==============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Authentication URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'printing:home'
LOGOUT_REDIRECT_URL = 'printing:home'


# ==============================================================================
# 5. INTERNATIONALIZATION & LOCALIZATION
# ==============================================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'  # Standard Indian Time
USE_I18N = True
USE_TZ = True


# ==============================================================================
# 6. STATIC AND MEDIA FILES (CSS, JS, Images, Uploaded Documents)
# ==============================================================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files: customer uploaded documents and generated QR codes
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ==============================================================================
# 7. SMARTPRINT KIOSK CONFIGURATION CONSTANTS
# ==============================================================================
# Maximum upload size in Megabytes and in Bytes
MAX_UPLOAD_SIZE_MB = int(os.getenv('MAX_UPLOAD_SIZE_MB', 15))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Allowed file extensions for document upload
ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']

# Printing mode: 'simulation' (default, safe for college demo) or 'worker' (physical printer)
PRINT_MODE = os.getenv('PRINT_MODE', 'simulation').strip().lower()

# Default pricing fallbacks in INR (Indian Rupees)
DEFAULT_BW_RATE = Decimal(os.getenv('DEFAULT_BW_RATE', '2.00'))
DEFAULT_COLOR_RATE = Decimal(os.getenv('DEFAULT_COLOR_RATE', '10.00'))
DEFAULT_DUPLEX_DISCOUNT = Decimal(os.getenv('DEFAULT_DUPLEX_DISCOUNT', '0.00'))
