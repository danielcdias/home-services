import logging
import ping3
import requests
import subprocess
import json

from typing import Tuple
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.utils import timezone

from core.util import SingletonMeta, log_error
from internet_status.models import (
    InternetProvider, HostsToPing, ConnectionStatus, ConnectionSpeed, StatusChoices,
    DailyStatusSummary, DailySpeedSummary, CheckTypeChoices
)

logger = logging.getLogger(__name__)


class InternetCheck(metaclass=SingletonMeta):

    def check_internet_status(self):
        providers: list[InternetProvider] = self._get_hosts()
        
        if not providers.exists():
            logger.warning("Nenhum InternetProvider habilitado encontrado. Status geral: UNKNOWN.")
            return

        for provider in providers:
            status, ping_results = self._ping(provider)
            if not self._save_ping_results(provider, ping_results, status):
                logger.error(f"Erro salvando resultado do ping para provider {provider.name}.")

    def check_internet_speed(self):
        providers: list[InternetProvider] = self._get_hosts()
        for provider in providers:
            speed_results = self._speedtest_official_cli(provider)
            if not self._save_speed_results(provider, speed_results):
                logger.error(f"Erro salvando resultado do speedtest para provider {provider.name}.")

    def _get_hosts(self) -> list[InternetProvider]:
        result: list[InternetProvider] = []
        try:
            result = InternetProvider.objects.filter(enabled=True).prefetch_related('hosts_to_ping')
        except Exception as ex:
            log_error(logger, "Erro ao buscar hosts para ping.", ex)
        return result

    def _ping(self, provider: InternetProvider) -> Tuple[str, dict]:
        hosts = provider.hosts_to_ping.filter(enabled=True)
        results = {'success': [], 'error': []}

        # Regra UNKNOWN: Menos de 2 hosts de cada tipo (ICMP e HTTP)
        icmp_hosts = hosts.filter(check_type=CheckTypeChoices.ICMP_PING)
        http_hosts = hosts.filter(check_type=CheckTypeChoices.HTTP_204)

        if icmp_hosts.count() < 2 or http_hosts.count() < 2:
            logger.info(f"Provider {provider.name} possui hosts insuficientes (Min: 2 ICMP, 2 HTTP). Status: UNKNOWN.")
            return StatusChoices.UNKNOWN, results

        for host in hosts:
            success = False
            detail = {}
            try:
                if host.check_type == CheckTypeChoices.HTTP_204:
                    # Teste HTTP 204
                    response = requests.get(host.hostname_or_ipaddress, timeout=5)
                    # 204 No Content é o esperado, mas aceitamos a faixa 2xx
                    if response.status_code == 204 or (200 <= response.status_code < 300):
                        success = True
                        detail = {'delay': round(response.elapsed.total_seconds() * 1000, 2)}
                    else:
                        detail = {'reason': f'HTTP Status {response.status_code}'}
                else:
                    # Teste ICMP Ping
                    delay = ping3.ping(host.hostname_or_ipaddress, timeout=2)
                    if delay:
                        success = True
                        detail = {'delay': round(delay * 1000, 2)}
                    else:
                        detail = {'reason': 'timeout'}
            except Exception as e:
                detail = {'reason': str(e)}

            entry = {'host': host.hostname_or_ipaddress, 'name': host.name, 'type': host.check_type}
            entry.update(detail)

            if success:
                results['success'].append(entry)
            else:
                results['error'].append(entry)

        total_tests = hosts.count()
        success_count = len(results['success'])

        # Regras Determinísticas de Status:
        if success_count == total_tests:
            status = StatusChoices.CONNECTED
        elif success_count == 0:
            status = StatusChoices.DISCONNECTED
        else:
            # Pelo menos um falhou, mas pelo menos um funcionou
            status = StatusChoices.UNSTABLE

        return status, results

    def _save_ping_results(self, provider: InternetProvider, results: dict, status: str) -> bool:
        try:
            ConnectionStatus.objects.create(
                provider=provider,
                status=status,
                ping_results=results
            )
            return True
        except Exception as ex:
            log_error(logger, "Erro ao salvar resultados do ping.", ex)
            return False

    def _save_speed_results(self, provider: InternetProvider, results: dict) -> bool:
        try:
            if 'exception' in results:
                return False
                
            ConnectionSpeed.objects.create(
                provider=provider,
                download_speed=results['download_speed_mbps'],
                upload_speed=results['upload_speed_mbps'],
                latency=results['latency_ms'],
                full_results=results
            )
            return True
        except Exception as ex:
            log_error(logger, "Erro ao salvar resultados do speedtest.", ex)
            return False

    def _speedtest_official_cli(self, provider: InternetProvider) -> dict:
        """
        Executa o speedtest-cli oficial da Ookla e retorna um dicionário com os resultados.
        Exige que o binário 'speedtest' esteja instalado no PATH.
        """
        result_data = {
            'download_speed_mbps': 0.0,
            'upload_speed_mbps': 0.0,
            'latency_ms': 0.0,
            'test_result': {}
        }

        try:
            # Comando base: speedtest --format=json --accept-license --accept-gdpr
            cmd = ["speedtest", "--format=json", "--accept-license", "--accept-gdpr"]
            
            # Se houver um ID de servidor específico configurado no provedor
            if provider.id_provider_speedtest:
                cmd.extend(["--server-id", str(provider.id_provider_speedtest)])

            logger.info(f"Iniciando Speedtest oficial para {provider.name}...")
            
            process = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(process.stdout)

            raw_download = data.get('download', {}).get('bandwidth', 0)
            raw_upload = data.get('upload', {}).get('bandwidth', 0)
            
            result_data['download_speed_mbps'] = round((raw_download * 8) / 1_000_000, 2)
            result_data['upload_speed_mbps'] = round((raw_upload * 8) / 1_000_000, 2)
            result_data['latency_ms'] = data.get('ping', {}).get('latency', 0.0)
            
            result_data['test_result'] = {
                'client': {
                    'ip': data.get('interface', {}).get('externalIp', 'Auto'),
                    'isp': data.get('isp', 'Local ISP')
                },
                'server': {
                    'name': data.get('server', {}).get('name', 'Nó Ookla'),
                    'sponsor': data.get('server', {}).get('location', 'Servidor'),
                    'country': data.get('server', {}).get('country', 'Global')
                }
            }
            
            logger.info(f"Speedtest Oficial Concluído: {result_data['download_speed_mbps']} Mbps ↓ / {result_data['upload_speed_mbps']} Mbps ↑")

        except Exception as e:
            error_msg = f"Falha no Speedtest Oficial Nativo: {e}"
            log_error(logger, error_msg, e)
            result_data['exception'] = error_msg
            
        return result_data

    def check_single_status(self, provider: InternetProvider):
        status, ping_results = self._ping(provider)
        if not self._save_ping_results(provider, ping_results, status):
            logger.error(f"Erro salvando resultado do ping para provider {provider.name}.")

    def check_single_speed(self, provider: InternetProvider):
        speed_results = self._speedtest_official_cli(provider)
        if not self._save_speed_results(provider, speed_results):
            logger.error(f"Erro salvando resultado do speedtest para provider {provider.name}.")


class InternetCleanup(metaclass=SingletonMeta):
    def run_monthly_cleanup(self):
        """
        Ponto de entrada para a tarefa agendada.
        """
        logger.info("Iniciando processo de limpeza e sumarização...")
        
        # Lê a variável de ambiente (padrão 2 meses caso não declarada)
        retention_months = getattr(settings, 'DATA_CLEANUP_RETENTION_MONTHS', 2)
        
        today = timezone.now().date()
        
        # Volta N meses com base na configuração para achar a Data Limite
        limit_date = today.replace(day=1)
        for _ in range(retention_months):
            limit_date = (limit_date - timedelta(days=1)).replace(day=1)
            
        try:
            with transaction.atomic():
                # Passamos o limite. Tudo MENOR que o limite será sumarizado
                self._summarize_status(limit_date)
                self._summarize_speed(limit_date)
                
                # Após sumarizar todo o passado, limpamos tudo que for MENOR que o limite
                ConnectionStatus.objects.filter(last_checked__date__lt=limit_date).delete()
                ConnectionSpeed.objects.filter(last_tested__date__lt=limit_date).delete()
                
                logger.info(f"Limpeza de dados anteriores a {limit_date.strftime('%d/%m/%Y')} concluída.")
        except Exception as ex:
            log_error(logger, "Erro na limpeza mensal", ex)
            raise ex

    def _summarize_status(self, limit_date):
        # Filtra tudo mais antigo que a data limite
        qs = ConnectionStatus.objects.filter(last_checked__date__lt=limit_date).values(
            'provider', 'last_checked__date'
        ).annotate(
            total=Count('id'),
            connected=Count('id', filter=Q(status=StatusChoices.CONNECTED)),
            unstable=Count('id', filter=Q(status=StatusChoices.UNSTABLE)),
            disconnected=Count('id', filter=Q(status=StatusChoices.DISCONNECTED)),
            unknown=Count('id', filter=Q(status=StatusChoices.UNKNOWN)),
        )

        for item in qs:
            total = item['total']
            if total > 0:
                conn_pct = (item['connected'] / total) * 100
                unst_pct = (item['unstable'] / total) * 100
                disc_pct = (item['disconnected'] / total) * 100
                unk_pct = (item['unknown'] / total) * 100
            else:
                conn_pct = unst_pct = disc_pct = unk_pct = 0
                
            DailyStatusSummary.objects.update_or_create(
                provider_id=item['provider'],
                date=item['last_checked__date'],
                defaults={
                    'total_checks': total,
                    'connected_pct': conn_pct,
                    'unstable_pct': unst_pct,
                    'disconnected_pct': disc_pct,
                    'unknown_pct': unk_pct
                }
            )

    def _summarize_speed(self, limit_date):
        # Filtra tudo mais antigo que a data limite
        qs = ConnectionSpeed.objects.filter(last_tested__date__lt=limit_date).values(
            'provider', 'last_tested__date'
        ).annotate(
            avg_down=Avg('download_speed'),
            avg_up=Avg('upload_speed'),
            avg_lat=Avg('latency')
        )

        for item in qs:
            DailySpeedSummary.objects.update_or_create(
                provider_id=item['provider'],
                date=item['last_tested__date'],
                defaults={
                    'avg_download': item['avg_down'],
                    'avg_upload': item['avg_up'],
                    'avg_latency': item['avg_lat']
                }
            )


def run_internet_cleanup_task():
    """
    Função de atalho para o scheduler chamar a limpeza mensal.
    """
    import logging
    from internet_status.services import InternetCleanup
    
    logger = logging.getLogger(__name__)
    logger.info(">>> [SCHEDULER] Executando a tarefa de limpeza via atalho...")
    
    try:
        InternetCleanup().run_monthly_cleanup()
        logger.info(">>> [SCHEDULER] Tarefa de limpeza finalizada com sucesso.")
    except Exception as e:
        logger.error(f">>> [SCHEDULER] Falha crítica na execução da limpeza: {str(e)}")
