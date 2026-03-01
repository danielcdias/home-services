from django.apps import AppConfig


class InternetStatusConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'internet_status'

    def ready(self):
        import internet_status.db_signals
