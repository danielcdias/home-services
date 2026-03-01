from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ConnectionSpeed, ConnectionStatus
from .alerts import check_and_alert_speed, check_and_alert_connection


@receiver(post_save, sender=ConnectionSpeed)
def trigger_speed_alert_check(sender, instance, created, **kwargs):
    """
    Escuta a criação de novos registros de velocidade e aciona a verificação de alertas.
    """
    if created:
        check_and_alert_speed(instance.provider_id)


@receiver(post_save, sender=ConnectionStatus)
def trigger_connection_alert_check(sender, instance, created, **kwargs):
    """
    Escuta a criação de novos registros de status (conectividade) e aciona a verificação de alertas.
    """
    if created:
        check_and_alert_connection(instance.provider_id)
