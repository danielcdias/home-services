import logging

from django.tasks import task

from internet_status.services import InternetCheck


logger = logging.getLogger(__name__)


@task
def check_internet_status():
    logger.info("Checking internet status...")
    InternetCheck().check_internet_status()


@task
def check_internet_speed():
    logger.info("Checking internet speed...")
    InternetCheck().check_internet_speed()
