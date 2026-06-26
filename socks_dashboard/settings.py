import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'btf-socks-dashboard-secret-key-2026-production'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'whitenoise.runserver_nostatic',
    'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'socks_dashboard.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'dashboard' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'socks_dashboard.wsgi.application'

# SQLite — Django app database (sessions, cache, config)
if 'RENDER' in os.environ:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': '/data/factory.db',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'factory.db',
        }
    }

# SQL Server — ERP source (read-only, not a Django managed DB)
MSSQL_CONFIG = {
    'SERVER': '81.17.87.85,1433',
    'DATABASE': 'BTFERPDB',
    'USERNAME': 'User1',
    'PASSWORD': 'bfzY7835WCS72M',
    'DRIVER': 'SQL Server',
    'TRUST_SERVER_CERTIFICATE': 'yes',
}

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'dashboard' / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Cache: in-memory per process — keeps heavy SQL queries cached for 4 minutes
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'TIMEOUT': 240,  # 4 minutes
    }
}

# Refresh interval in seconds pushed to the frontend
DASHBOARD_REFRESH_SECONDS = 300  # 5 minutes polling fallback
