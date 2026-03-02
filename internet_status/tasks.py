import logging

from internet_status.services import InternetCheck
from internet_status.models import InternetProvider

logger = logging.getLogger(__name__)


def check_internet_status(provider_id=None):
    if provider_id:
        logger.info(f"Checking internet status (Provider ID {provider_id})...")
        try:
            provider = InternetProvider.objects.get(
                id=provider_id, enabled=True)
            InternetCheck().check_single_status(provider)
        except InternetProvider.DoesNotExist:
            pass
    else:
        logger.info("Checking internet status (Todos)...")
        InternetCheck().check_internet_status()


def check_internet_speed(provider_id=None):
    if provider_id:
        logger.info(f"Checking internet speed (Provider ID {provider_id})...")
        try:
            provider = InternetProvider.objects.get(
                id=provider_id, enabled=True)
            InternetCheck().check_single_speed(provider)
        except InternetProvider.DoesNotExist:
            pass
    else:
        logger.info("Checking internet speed (Todos)...")
        InternetCheck().check_internet_speed()
