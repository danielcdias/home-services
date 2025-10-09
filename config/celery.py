import os

from celery import Celery
from celery.signals import setup_logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

CELERY_APP_NAME = os.getenv('CELERY_APP_NAME', 'home_services')

app = Celery(CELERY_APP_NAME)
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.broker_connection_retry_on_startup = True
app.autodiscover_tasks()

CELERY_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'celery-format': {
            'format': '%(asctime)-23s [%(levelname)s] (%(name)s:%(lineno)d) [%(processName)s] - %(message)s',
        }
    },
    'handlers': {
        'console_log': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'celery-format',
        },
    },
    'loggers': {
        'root': {
            'handlers': ['console_log'],
            'level': 'INFO',
        },
        'celery': {
            'handlers': ['console_log'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}


@setup_logging.connect
def config_loggers(*args, **kwargs):
    from logging.config import dictConfig
    dictConfig(CELERY_LOGGING)


@app.task(bind=True, ignore_result=True)
def debug_task(self) -> None:
    print(f'Request: {self.request!r}')
