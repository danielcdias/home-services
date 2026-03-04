import logging

from pathlib import Path
from django.conf import settings
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver

from .models import ConnectionSpeed, ConnectionStatus, InternetProvider
from .alerts import check_and_alert_speed, check_and_alert_connection


logger = logging.getLogger(__name__)


@receiver(post_save, sender=ConnectionSpeed)
def trigger_speed_alert_check(sender, instance, created, **kwargs):
    """
    Escuta a criação de novos registros de velocidade e aciona a verificação de alertas.
    """
    logger.info(f"Triggering speed alert check for provider ID: {instance.provider_id}, created: {created}")
    if created:
        check_and_alert_speed(instance.provider_id)


@receiver(post_save, sender=ConnectionStatus)
def trigger_connection_alert_check(sender, instance, created, **kwargs):
    """
    Escuta a criação de novos registros de status (conectividade) e aciona a verificação de alertas.
    """
    logger.info(f"Triggering connection alert check for provider ID: {instance.provider_id}, created: {created}")
    if created:
        check_and_alert_connection(instance.provider_id)


# ==========================================
# Gatilhos de Reload do Scheduler
# ==========================================

def _create_reload_flag():
    """Função auxiliar para criar o arquivo de flag."""
    shared_dir = Path(settings.BASE_DIR) / 'shared'
    shared_dir.mkdir(exist_ok=True) # Garante que a pasta existe
    
    flag_file = shared_dir / 'reload_scheduler.flag'
    flag_file.touch(exist_ok=True)


@receiver(pre_save, sender=InternetProvider)
def check_provider_changes(sender, instance, **kwargs):
    """
    Verifica se os campos de agendamento foram alterados antes de salvar.
    """
    logger.debug(f"Checking for changes in InternetProvider: {instance.name}, pk: {instance.pk}")
    # Se o objeto já tem 'pk', significa que já existe no banco (é um UPDATE)
    if instance.pk:
        try:
            # Busca a versão antiga direto do banco de dados
            old_instance = InternetProvider.objects.get(pk=instance.pk)

            # Verifica se os intervalos ou o status de ativação mudaram
            if (old_instance.status_check_interval != instance.status_check_interval or
                old_instance.speed_test_interval != instance.speed_test_interval or
                    old_instance.enabled != instance.enabled):

                # Anota na instância atual que houve mudança relevante
                instance._schedule_changed = True
            else:
                instance._schedule_changed = False
        except InternetProvider.DoesNotExist:
            pass


@receiver(post_save, sender=InternetProvider)
def flag_scheduler_reload_on_save(sender, instance, created, **kwargs):
    """
    Cria a flag apenas se for uma inclusão nova ou se houver alteração nos intervalos/enabled.
    """
    # Se foi criado (INSERT) ou se o pre_save anotou que houve mudança relevante
    logger.debug(f"Post-save for InternetProvider: {instance.name}, created: {created}, schedule_changed: {getattr(instance, '_schedule_changed', False)}")
    if created or getattr(instance, '_schedule_changed', False):
        _create_reload_flag()


@receiver(post_delete, sender=InternetProvider)
def flag_scheduler_reload_on_delete(sender, instance, **kwargs):
    """
    Cria a flag se um provedor for excluído (DELETE), para removê-lo da agenda atual.
    """
    logger.debug("Post-delete for InternetProvider")
    _create_reload_flag()
