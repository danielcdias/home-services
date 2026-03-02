import environ
import logging
import os

from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path


LOCAL_DEV_ENV = os.environ.get('DEV_ENV', False)

env = environ.Env(
    DEBUG=(bool, False),
    TZ=(str, 'America/Sao_Paulo'),
    DJANGO_SECRET_KEY=(
        str, 'django-insecure-j@@b0)u$5*hgnoy02u1)qv6c*nv$%ib@+k(x!58bz229)bb1x#'),
    DJANGO_ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
    DJANGO_DATABASE_URL=(str, 'sqlite:///db.sqlite3'),
)

BASE_DIR = Path(__file__).resolve().parent.parent

environ.Env.read_env(os.path.join(
    BASE_DIR,
    '.env.local_dev' if LOCAL_DEV_ENV else '.env')
)

SECRET_KEY = env('DJANGO_SECRET_KEY')

DEBUG = env('DEBUG')

ALLOWED_HOSTS = env('DJANGO_ALLOWED_HOSTS')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'core',
    'internet_status',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

if LOCAL_DEV_ENV:
    DATABASES = {
        'default': env.db_url_config('sqlite:///db.sqlite3')
    }
else:
    DATABASES = {
        'default': env.db('DJANGO_DATABASE_URL'),
    }

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = env('TZ')
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/
STATIC_ROOT = BASE_DIR / 'static'
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# TIME_ZONE já deve estar definido acima no seu settings.py (TIME_ZONE = env('TZ'))


class LocalTimeFormatter(logging.Formatter):
    """Força o logging a usar o TIME_ZONE do Django, ignorando o relógio do SO."""

    def converter(self, timestamp):
        dt = datetime.fromtimestamp(timestamp, tz=ZoneInfo(TIME_ZONE))
        return dt.timetuple()


LOG_LEVEL = env('LOG_LEVEL', default='INFO')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'django-format': {
            '()': LocalTimeFormatter,
            'format': '%(asctime)-23s [%(levelname)s] (%(name)s:%(lineno)d) [%(processName)s] - %(message)s',
        }
    },
    'handlers': {
        'console_stdout': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'django-format',
            'stream': 'ext://sys.stdout',
        },
    },
    'loggers': {
        'root': {
            'handlers': ['console_stdout'],
            'level': 'INFO',
        },
        'django': {
            'handlers': ['console_stdout'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console_stdout'],
            'level': 'INFO',
            'propagate': False,
        },
        'django_tasks': {
            'handlers': ['console_stdout'],
            'level': 'INFO',
            'propagate': False,
        },
        'config': {
            'handlers': ['console_stdout'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'core': {
            'handlers': ['console_stdout'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'internet_status': {
            'handlers': ['console_stdout'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}

# --- Configurações para Reverse Proxy (Nginx) ---
# Confia nos cabeçalhos enviados pelo proxy
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# --- Configurações MailerSend
MAILERSEND_API_KEY = env('MAILERSEND_API_KEY', default='')
SENDER_EMAIL = env('MAILERSEND_SENDER_EMAIL',
                   default='noreplay@danieldias.dev.br')
SENDER_NAME = env(
    'SENDER_NAME', default='Monitor de Rede - Casa Dani & Stephie')
