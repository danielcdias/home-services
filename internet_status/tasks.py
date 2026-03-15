import logging
import time
import random
from datetime import datetime
from croniter import croniter

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
    # Se rodar sem provider (manualmente via shell, por exemplo), faz logo direto
    if not provider_id:
        logger.info("Checking internet speed (Todos) sem janela de atraso...")
        InternetCheck().check_internet_speed()
        return

    try:
        provider = InternetProvider.objects.get(id=provider_id, enabled=True)
    except InternetProvider.DoesNotExist:
        return

    delay_seconds = 0
    
    # --- CÁLCULO DINÂMICO DA JANELA VIA CRON ---
    if provider.speed_test_interval and croniter.is_valid(provider.speed_test_interval):
        now = datetime.now()
        cron = croniter(provider.speed_test_interval, now)
        
        # Simula quando será a PRÓXIMA execução a partir de agora
        next_run = cron.get_next(datetime)
        
        # O tamanho da janela é a diferença entre agora e a próxima vez
        window_seconds = (next_run - now).total_seconds()
        
        # Margem de segurança de 10 minutos (600s) para garantir que o teste conclua
        # bem antes de a próxima janela começar.
        max_delay = int(window_seconds) - 600
        
        if max_delay > 0:
            # Sorteia qualquer segundo na janela válida (ex: 3h, 6h, etc.)
            delay_seconds = random.randint(0, max_delay)
        else:
            # Trava de Segurança: Se você configurar o CRON para um intervalo muito curto 
            # (ex: 5 em 5 minutos para debug), ele faz um jitter curtinho proporcional.
            safe_max = max(1, int(window_seconds) - 10)
            delay_seconds = random.randint(1, safe_max)

    hours = delay_seconds // 3600
    minutes = (delay_seconds % 3600) // 60
    seconds = delay_seconds % 60
    
    logger.info(
        f"Janela de Speedtest aberta (Provider ID {provider_id}). O teste real ocorrerá daqui a "
        f"{hours}h {minutes}m {seconds}s (Atraso sorteado: {delay_seconds}s)."
    )
    
    # A Thread independente fica pausada aqui. O scheduler principal continua livre.
    if delay_seconds > 0:
        time.sleep(delay_seconds)

    # --- EXECUÇÃO REAL APÓS O TEMPO SORTEADO ---
    logger.info(f"Iniciando a execução real do speedtest Ookla (Provider ID {provider_id})...")
    InternetCheck().check_single_speed(provider)
