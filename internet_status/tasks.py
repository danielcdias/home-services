import logging

from celery import shared_task
from celery.signals import worker_ready

from core.util import log_error
from internet_status import scheduler


logger = logging.getLogger(__name__)


class ReadyToRun:
    READY: bool = False

# TODO Melhorar o log para incluir o app sem ter que incluir na mensagem.
# TODO Ver porque log do celery está duplicado.


@worker_ready.connect
def worker_ready_event(sender, **kwargs):
    logger.info(
        "(Internet Status) worker_ready.connect - worker_ready_event({})".format(sender))
    try:
        with sender.app.connection() as conn:
            sender.app.send_task(
                'internet_status.tasks.setup', connection=conn)
    except Exception as ex:
        log_error(
            logger, "(Internet Status) Erro enfileirando task 'engine.tasks.setup'.", ex)


@shared_task
def setup():
    try:
        ReadyToRun.READY = True
        scheduler.start()
    except Exception as ex:
        log_error(logger, "(Internet Status) Erro chamando scheduler.start().", ex)


@shared_task(name='internet_status.check_internet_status')
def check_internet_status():
    # TODO Implementar
    logger.info("(Internet Status) Checking internet status...")


@shared_task(name='internet_status.check_internet_speed')
def check_internet_speed():
    # TODO Implementar
    logger.info("(Internet Status) Checking internet speed...")
