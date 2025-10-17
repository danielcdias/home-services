import logging
import json

from django_celery_beat.models import PeriodicTask, CrontabSchedule, IntervalSchedule
from django.conf import settings

from internet_status.models import InternetProvider

logger = logging.getLogger(__name__)

# TODO Ler intervalos do banco de dados (InternetProvider)


def start():
    """
    Cria ou atualiza as tarefas periódicas no banco de dados.
    """
    logger.info("Agendando tarefas do módulo Internet Status...")

    # TODO Testar
    try:
        providers: list[InternetProvider] = InternetProvider.objects.filter(
            enabled=True).prefetch_related('hosts_to_ping')
        for provider in providers:
            schedule_status, _ = IntervalSchedule.objects.get_or_create(
                every=provider.status_check_interval,
                period=IntervalSchedule.MINUTES
            )
            PeriodicTask.objects.update_or_create(
                name=f'[{provider.name}] Check Internet Status',
                defaults={
                    'task': 'internet_status.check_internet_status',
                    'interval': schedule_status,
                    'enabled': True,
                }
            )

            schedule_speed, _ = IntervalSchedule.objects.get_or_create(
                every=provider.speed_test_interval,
                period=IntervalSchedule.MINUTES
            )

            PeriodicTask.objects.update_or_create(
                name=f'[{provider.name}] Check Internet Speed',
                defaults={
                    'task': 'internet_status.check_internet_speed',
                    'interval': schedule_speed,
                    'enabled': True,
                }
            )

    except Exception as ex:
        logger.error(f"Erro agendando tarefas do módulo Internet Status: {ex}")
        raise ex
