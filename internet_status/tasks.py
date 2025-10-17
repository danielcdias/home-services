import logging

from celery import shared_task
from celery.signals import worker_ready

from core.util import log_error
from internet_status import scheduler
from internet_status.services import InternetCheck


logger = logging.getLogger(__name__)


class ReadyToRun:
    READY: bool = False


@worker_ready.connect
def worker_ready_event(sender, **kwargs):
    logger.info(
        "worker_ready.connect - worker_ready_event({})".format(sender))
    try:
        with sender.app.connection() as conn:
            sender.app.send_task(
                'internet_status.tasks.setup', connection=conn)
    except Exception as ex:
        log_error(
            logger, "Erro enfileirando task 'engine.tasks.setup'.", ex)


@shared_task
def setup():
    try:
        ReadyToRun.READY = True
        scheduler.start()
    except Exception as ex:
        log_error(logger, "Erro chamando scheduler.start().", ex)


@shared_task(name='internet_status.check_internet_status')
def check_internet_status():
    logger.info("Checking internet status...")
    InternetCheck().check_internet_status()


@shared_task(name='internet_status.check_internet_speed')
def check_internet_speed():
    logger.info("Checking internet speed...")
    InternetCheck().check_internet_speed()
