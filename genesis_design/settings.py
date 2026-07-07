import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='django-insecure-genesis-design-dev-key')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])


def _build_csrf_trusted_origins():
    """Trust browser origins for ALLOWED_HOSTS on common app ports (IP/LAN deploys)."""
    explicit = env.list('CSRF_TRUSTED_ORIGINS', default=[])
    if explicit:
        return explicit

    hosts = [h.strip() for h in ALLOWED_HOSTS if h.strip() and h.strip() != '*']
    ports = env.list('APP_PORTS', default=['8000', '8030'])
    origins = []
    for host in hosts:
        for port in ports:
            origins.append(f'http://{host}:{port}')
        origins.append(f'http://{host}')
        origins.append(f'https://{host}')
        for port in ports:
            origins.append(f'https://{host}:{port}')
    return list(dict.fromkeys(origins))


CSRF_TRUSTED_ORIGINS = _build_csrf_trusted_origins()

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'crispy_tailwind',
    'rest_framework',
    'apps.accounts',
    'apps.core',
    'apps.projects',
    'apps.designs',
    'apps.systems',
    'apps.workflow',
    'apps.notifications',
    'apps.reports',
    'apps.analytics',
    'apps.api',
    'apps.permissions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middleware.AuditMiddleware',
    'apps.permissions.middleware.ProjectContextMiddleware',
]

ROOT_URLCONF = 'genesis_design.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.csrf',
                'apps.notifications.context_processors.unread_notifications',
                'apps.permissions.context_processors.user_permissions',
            ],
        },
    },
]

WSGI_APPLICATION = 'genesis_design.wsgi.application'


def _database_config():
    """Prefer DB_* variables; fall back to DATABASE_URL."""
    if env('DB_NAME', default=None):
        return {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': env('DB_NAME'),
                'USER': env('DB_USER'),
                'PASSWORD': env('DB_PASSWORD'),
                'HOST': env('DB_HOST', default='localhost'),
                'PORT': env('DB_PORT', default='5432'),
                'CONN_MAX_AGE': 60,
            }
        }
    return {
        'default': env.db(
            'DATABASE_URL',
            default='postgres://genesis_admin@localhost:5432/genesis_design',
        ),
    }


DATABASES = _database_config()

# Use SQLite for test runs when PostgreSQL is unavailable locally.
import sys
if 'test' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'test_db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dhaka'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'
SERVE_MEDIA = env.bool('SERVE_MEDIA', default=False)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'accounts.User'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'tailwind'
CRISPY_TEMPLATE_PACK = 'tailwind'

EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@genesisdesign.local')

CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Start deadline status/escalation checks inside runserver (no Docker/Redis required).
DEADLINE_AUTO_SCHEDULER = env.bool('DEADLINE_AUTO_SCHEDULER', default=True)

try:
    from genesis_design.celery_beat_schedule import CELERY_BEAT_SCHEDULE  # noqa: E402, F401
except ImportError:
    CELERY_BEAT_SCHEDULE = {}
