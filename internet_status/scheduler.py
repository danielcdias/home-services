import logging
import json

from django_celery_beat.models import PeriodicTask, CrontabSchedule, IntervalSchedule
from django.conf import settings

logger = logging.getLogger(__name__)


# TODO Configurar corretamente os horários de execução das tarefas.

def start():
    """
    Cria ou atualiza as tarefas periódicas no banco de dados.
    """
    logger.info("(Internet Status) Iniciando agendador de tarefas...")

    schedule_interval, _ = IntervalSchedule.objects.get_or_create(
        every=11,
        period=IntervalSchedule.SECONDS,
    )

    PeriodicTask.objects.update_or_create(
        name='Check Internet Status',
        defaults={
            'task': 'internet_status.check_internet_status',
            'interval': schedule_interval,
            'enabled': True,
        }
    )

    schedule_crontab, _ = CrontabSchedule.objects.get_or_create(
        minute='1',      # Todo minuto
        hour='*',        # Toda hora
        day_of_week='*',  # Todo dia da semana
        day_of_month='*',  # Todo dia do mês
        month_of_year='*',  # Todo mês do ano
        timezone=settings.TIME_ZONE
    )

    PeriodicTask.objects.update_or_create(
        name='Check Internet Speed',
        defaults={
            'task': 'periodic_cleainternet_status.check_internet_speednup',
            'crontab': schedule_crontab,
            'enabled': True,
        }
    )

    logger.info("(Internet Status) Agendador de tarefas finalizado.")
