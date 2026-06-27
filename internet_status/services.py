import logging
import ping3
import requests
import subprocess
import json

from typing import Tuple
from datetime import timedelta, date

from django.conf import settings
from django.db import transaction
from django.db.models import Avg, Count, Q, Case, When, Value, FloatField
from django.db.models.functions import TruncMonth
from django.utils import timezone

from core.util import SingletonMeta, log_error
from internet_status.models import (
    InternetProvider, HostsToPing, ConnectionStatus, ConnectionSpeed, StatusChoices,
    DailyStatusSummary, DailySpeedSummary, CheckTypeChoices, MonthlyInternetSummary
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

    def get_monthly_indicators(self, provider, year, month):
        """
        Calcula os indicadores mensais: conectividade e médias de velocidade.
        Considera dados sumarizados para meses fechados ou brutos para o mês corrente.
        """
        # Tenta buscar no resumo (mês fechado)
        summary = MonthlyInternetSummary.objects.filter(
            provider=provider, year=year, month=month
        ).first()

        if summary:
            return {
                'connectivity': summary.avg_connectivity,
                'download': summary.avg_download,
                'upload': summary.avg_upload,
                'download_pct': summary.download_pct_contracted,
                'upload_pct': summary.upload_pct_contracted
            }

        # Cálculo para mês aberto (dados brutos)
        status_qs = ConnectionStatus.objects.filter(
            provider=provider, last_checked__year=year, last_checked__month=month
        ).aggregate(
            avg_conn=Avg(Case(When(status=StatusChoices.CONNECTED, then=Value(1.0)),
                         default=Value(0.0), output_field=FloatField()))
        )

        speed_qs = ConnectionSpeed.objects.filter(
            provider=provider, last_tested__year=year, last_tested__month=month
        ).aggregate(avg_down=Avg('download_speed'), avg_up=Avg('upload_speed'))

        conn = (status_qs['avg_conn'] or 0) * 100
        down = speed_qs['avg_down'] or 0
        up = speed_qs['avg_up'] or 0
        c_down = float(provider.contracted_download_speed)
        c_up = float(provider.contracted_upload_speed)

        return {
            'connectivity': round(conn, 2),
            'download': round(down, 2),
            'upload': round(up, 2),
            'download_pct': round((down / c_down * 100), 2) if c_down > 0 else 0,
            'upload_pct': round((up / c_up * 100), 2) if c_up > 0 else 0
        }

    def _get_hosts(self) -> list[InternetProvider]:
        result: list[InternetProvider] = []
        try:
            result = InternetProvider.objects.filter(enabled=True).prefetch_related('hosts_to_ping')
        except Exception as ex:
            log_error(logger, "Erro ao buscar hosts para ping.", ex)
        return result

    def _ping(self, provider: InternetProvider) -> Tuple[str, dict]:
        hosts: list[HostsToPing] = provider.hosts_to_ping.filter(enabled=True)
        
        # Estrutura de dados original para garantir compatibilidade com a UI (views.py)
        results = {
            "thresholds": {
                "reason": "",
                "calculation": {
                    "http_total": 0,
                    "icmp_total": 0,
                    "http_success": 0,
                    "icmp_loss_pct": 0,
                    "avg_icmp_latency": 0
                }
            },
            "tests_results": []
        }

        # Requisito Mínimo Flexibilizado: Mínimo de 2 hosts ativos no total para realizar a medição
        if hosts.count() < 2:
            results["thresholds"]["reason"] = f"Hosts insuficientes cadastrados (Min: 2 ativos no total. Cadastrados/Ativos: {hosts.count()})."
            return StatusChoices.UNKNOWN, results

        icmp_latencies = []
        http_success_count = 0
        
        for host in hosts:
            success = False
            result_val = None
            exception_msg = None
            
            try:
                if host.check_type == CheckTypeChoices.HTTP_204:
                    results["thresholds"]["calculation"]["http_total"] += 1
                    # Teste HTTP 204
                    response = requests.get(host.hostname_or_ipaddress, timeout=5)
                    result_val = round(response.elapsed.total_seconds() * 1000, 2)
                    if response.status_code == 204 or (200 <= response.status_code < 300):
                        success = True
                        http_success_count += 1
                    else:
                        exception_msg = f"HTTP Status {response.status_code}"
                else:
                    results["thresholds"]["calculation"]["icmp_total"] += 1
                    # Teste ICMP Ping
                    # ping3.ping returns delay in seconds or None/False on failure
                    delay = ping3.ping(host.hostname_or_ipaddress, timeout=2)
                    if delay:
                        success = True
                        result_val = round(delay * 1000, 2)
                        icmp_latencies.append(result_val)
                    else:
                        exception_msg = "timeout"
            except Exception as e:
                exception_msg = str(e)

            # Popula tests_results para consumo direto do frontend/UI
            results["tests_results"].append({
                "name": host.name,
                "result": result_val,
                "success": success,
                "exception": exception_msg,
                "check_type": "HTTP" if host.check_type == CheckTypeChoices.HTTP_204 else "ICMP",
                "hostname_or_ipaddress": host.hostname_or_ipaddress
            })

        # Processamento dos cálculos para o dicionário calculation
        total_icmp = results["thresholds"]["calculation"]["icmp_total"]
        icmp_success = len(icmp_latencies)
        
        avg_latency = round(sum(icmp_latencies) / icmp_success, 2) if icmp_success > 0 else 0
        loss_pct = round(((total_icmp - icmp_success) / total_icmp) * 100, 2) if total_icmp > 0 else 0
        
        results["thresholds"]["calculation"]["http_success"] = http_success_count
        results["thresholds"]["calculation"]["icmp_loss_pct"] = loss_pct
        results["thresholds"]["calculation"]["avg_icmp_latency"] = avg_latency

        # Nova Lógica de Atribuição de Status (Percentual de Sucesso):
        # - CONNECTED: Taxa de sucesso >= 66% (Tolerância a falhas de hosts de teste individuais)
        # - DISCONNECTED: Taxa de sucesso == 0%
        # - UNSTABLE: Taxa de sucesso entre 0% e 66% (exclusivo)
        total_tests = hosts.count()
        total_success = http_success_count + icmp_success
        success_rate = (total_success / total_tests) * 100 if total_tests > 0 else 0

        if total_success == 0:
            status = StatusChoices.DISCONNECTED
            results["thresholds"]["reason"] = f"Falha total em todos os {total_tests} testes de conectividade executados."
        elif success_rate >= 66.0:
            status = StatusChoices.CONNECTED
            results["thresholds"]["reason"] = f"Conectividade validada com sucesso ({total_success}/{total_tests} testes bem-sucedidos, {success_rate:.1f}%)."
        else:
            status = StatusChoices.UNSTABLE
            results["thresholds"]["reason"] = f"Conectividade parcial/instável detectada ({total_success}/{total_tests} testes bem-sucedidos, {success_rate:.1f}%)."

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

    def run_monthly_summarization(self):
        """
        Gera o resumo consolidado para TODOS os meses passados que ainda 
        não foram processados e que possuem dados no banco.
        """
        logger.info("Iniciando sumarização retroativa de indicadores mensais...")
        
        # Usamos timezone.now() para obter um datetime 'aware'
        now = timezone.now()
        first_day_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        providers = InternetProvider.objects.filter(enabled=True)
        checker = InternetCheck()

        for provider in providers:
            # Identifica meses com dados de velocidade anteriores ao mês atual
            speed_months = ConnectionSpeed.objects.filter(
                provider=provider, 
                last_tested__lt=first_day_current_month
            ).annotate(
                month_date=TruncMonth('last_tested')
            ).values_list('month_date', flat=True).distinct()

            # Identifica meses com dados de status anteriores ao mês atual
            status_months = ConnectionStatus.objects.filter(
                provider=provider, 
                last_checked__lt=first_day_current_month
            ).annotate(
                month_date=TruncMonth('last_checked')
            ).values_list('month_date', flat=True).distinct()

            # Une as listas de meses únicos encontrados
            all_months = sorted(list(set(list(speed_months) + list(status_months))))

            for m_date in all_months:
                year, month = m_date.year, m_date.month

                # Verifica se já existe resumo para este provedor/mês/ano
                exists = MonthlyInternetSummary.objects.filter(
                    provider=provider, year=year, month=month
                ).exists()

                if not exists:
                    logger.info(f"Sumarizando dados para {provider.name}: {month}/{year}")
                    m = checker.get_monthly_indicators(provider, year, month)
                    
                    # Cria o resumo se houver qualquer dado relevante
                    if m['connectivity'] > 0 or m['download'] > 0:
                        MonthlyInternetSummary.objects.create(
                            provider=provider,
                            year=year,
                            month=month,
                            avg_connectivity=m['connectivity'],
                            avg_download=m['download'],
                            avg_upload=m['upload'],
                            download_pct_contracted=m['download_pct'],
                            upload_pct_contracted=m['upload_pct']
                        )

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
    
    try:
        InternetCleanup().run_monthly_cleanup()
        logger.info("[SCHEDULER] Tarefa de limpeza finalizada com sucesso.")
    except Exception as e:
        logger.error(f"[SCHEDULER] Falha crítica na execução da limpeza: {str(e)}")
