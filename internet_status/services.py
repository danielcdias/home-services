import logging
import ping3
import requests
import subprocess
import json
import os
import shlex

from typing import Tuple

from django.conf import settings
from core.util import SingletonMeta, log_error
from internet_status.models import InternetProvider, HostsToPing, ConnectionStatus, ConnectionSpeed, StatusChoices

logger = logging.getLogger(__name__)


class InternetCheck(metaclass=SingletonMeta):

    def check_internet_status(self):
        providers: list[InternetProvider] = self._get_hosts()
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
            log_error(logger, "Erro obtendo providers de internet.", ex)
        return result

    def _save_ping_results(self, provider: InternetProvider, ping_results: dict, status: str) -> bool:
        result: bool = False
        try:
            ConnectionStatus.objects.create(
                provider=provider,
                status=status,
                ping_results=ping_results
            )
            result = True
        except Exception as ex:
            log_error(logger, "Erro salvando resultado do ping.", ex)
        return result

    def _ping(self, provider: InternetProvider) -> Tuple[StatusChoices, dict]:
        result_status: StatusChoices = StatusChoices.UNKNOWN
        result_data: dict = {'tests_results': [], 'thresholds': {}}
        
        hosts_to_test = HostsToPing.objects.filter(provider=provider, enabled=True)
        
        http_total = 0
        http_success = 0
        icmp_total = 0
        icmp_success = 0
        total_icmp_latency = 0.0

        for host in hosts_to_test:
            result = {
                'name': host.name,
                'hostname_or_ipaddress': host.hostname_or_ipaddress,
                'check_type': host.check_type,
                'result': 0, 
                'success': False,
                'exception': None,
            }

            if host.check_type == 'HTTP':
                http_total += 1
                try:
                    import urllib3
                    urllib3.disable_warnings()
                    response = requests.get(host.hostname_or_ipaddress, timeout=3, verify=False)
                    if response.status_code == 204:
                        result['success'] = True
                        result['result'] = response.elapsed.total_seconds() * 1000
                        http_success += 1
                    else:
                        result['exception'] = f"Status inesperado: {response.status_code}"
                except requests.exceptions.RequestException as ex:
                    result['exception'] = str(ex)

            elif host.check_type == 'ICMP':
                icmp_total += 1
                try:
                    ping_result = ping3.ping(host.hostname_or_ipaddress, timeout=2)
                    if ping_result is not False and ping_result is not None:
                        result['success'] = True
                        result['result'] = ping_result * 1000 
                        icmp_success += 1
                        total_icmp_latency += result['result']
                    else:
                        result['exception'] = "Timeout"
                except Exception as ex:
                    log_error(logger, "Erro executando ping ICMP.", ex)
                    result['exception'] = str(ex)
                    
            result_data['tests_results'].append(result)

        total_hosts = http_total + icmp_total
        icmp_loss_pct = 0.0
        avg_icmp_latency = 0.0
        
        if icmp_total > 0:
            icmp_loss_pct = ((icmp_total - icmp_success) / icmp_total) * 100
            if icmp_success > 0:
                avg_icmp_latency = total_icmp_latency / icmp_success

        result_data['thresholds'] = {
            'provider_config': {
                'minimum_hosts_to_ping': provider.minimum_hosts_to_ping,
                'unstable_packet_loss_threshold': float(provider.unstable_packet_loss_threshold),
                'unstable_latency_threshold': float(provider.unstable_latency_threshold),
            },
            'calculation': {
                'http_total': http_total,
                'http_success': http_success,
                'icmp_total': icmp_total,
                'icmp_loss_pct': round(icmp_loss_pct, 2),
                'avg_icmp_latency': round(avg_icmp_latency, 2),
            },
            'reason': ''
        }
        
        if total_hosts < provider.minimum_hosts_to_ping:
            result_status = StatusChoices.UNKNOWN
            result_data['thresholds']['reason'] = f"Apenas {total_hosts} hosts configurados. Mínimo exigido: {provider.minimum_hosts_to_ping}."
            return result_status, result_data

        if http_total > 0 and http_success == 0:
            result_status = StatusChoices.DISCONNECTED
            result_data['thresholds']['reason'] = "FALHA CRÍTICA: Nenhum teste HTTP 204 obteve sucesso. Possível falha de DNS ou bloqueio na camada 7."
            return result_status, result_data
            
        if http_total == 0 and icmp_total > 0 and icmp_success == 0:
            result_status = StatusChoices.DISCONNECTED
            result_data['thresholds']['reason'] = "FALHA CRÍTICA: 100% de perda de pacotes ICMP (Nenhum teste HTTP configurado)."
            return result_status, result_data

        if icmp_loss_pct >= provider.unstable_packet_loss_threshold:
            result_status = StatusChoices.UNSTABLE
            result_data['thresholds']['reason'] = f"DEGRADAÇÃO: Perda de pacotes ICMP ({icmp_loss_pct:.1f}%) ultrapassou o limite ({provider.unstable_packet_loss_threshold}%)."
        elif avg_icmp_latency >= provider.unstable_latency_threshold:
            result_status = StatusChoices.UNSTABLE
            result_data['thresholds']['reason'] = f"DEGRADAÇÃO: Latência média ICMP ({avg_icmp_latency:.1f}ms) ultrapassou o limite ({provider.unstable_latency_threshold}ms)."
        else:
            result_status = StatusChoices.CONNECTED
            result_data['thresholds']['reason'] = "NORMAL: Conectividade validada com sucesso na Camada 7 e limites de ICMP normais."

        return result_status, result_data

    def _save_speed_results(self, provider: InternetProvider, speed_results: dict) -> bool:
        result: bool = False
        try:
            ConnectionSpeed.objects.create(
                provider=provider,
                download_speed=speed_results.get('download_speed_mbps', 0),
                upload_speed=speed_results.get('upload_speed_mbps', 0),
                latency=speed_results.get('latency_ms', 0),
                full_results=speed_results
            )
            result = True
        except Exception as ex:
            log_error(logger, "Erro salvando resultado do speedtest.", ex)
        return result

    def _speedtest_official_cli(self, provider: InternetProvider) -> dict:
        """Motor Definitivo: Executa comando extraído das configurações do Django (settings.py)."""
        result_data = {
            'download_speed_mbps': 0, 'upload_speed_mbps': 0, 'latency_ms': 0,
            'test_result': {}, 'exception': None,
            'thresholds': {
                'provider_config': {
                    'download_speed_minimum_threshold': provider.download_speed_minimum_threshold,
                    'download_speed_expected_threshold': provider.download_speed_expected_threshold,
                    'upload_speed_minimum_threshold': provider.upload_speed_minimum_threshold,
                    'upload_speed_expected_threshold': provider.upload_speed_expected_threshold,
                }
            }
        }

        try:
            logger.info("Iniciando Speedtest: CLI gerido via Django Settings...")
            
            # Obtém a string de comando configurada no settings.py
            # Usa getattr para prever um fallback caso a variável falte no ambiente
            cmd_string = getattr(settings, 'OOKLA_CLI_COMMAND', 'speedtest --accept-license --accept-gdpr -f json')
            
            # O parâmetro posix=(os.name != 'nt') é vital. 
            # Ele impede que o shlex engula barras invertidas (\) em caminhos no Windows.
            cmd = shlex.split(cmd_string, posix=(os.name != 'nt'))
            
            try:
                process = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            except FileNotFoundError:
                raise Exception(f"Binário não encontrado. Verifique se o caminho na variável OOKLA_CLI_COMMAND em settings.py está correto: {cmd_string}")

            raw_out = process.stdout.strip()
            raw_err = process.stderr.strip()

            if process.returncode != 0:
                raise Exception(f"O CLI nativo falhou (Código {process.returncode}). STDERR: '{raw_err}' | STDOUT: '{raw_out}'")

            if not raw_out:
                raise Exception(f"O comando rodou, mas retornou vazio. STDERR: '{raw_err}'")

            try:
                data = json.loads(raw_out)
            except json.JSONDecodeError:
                raise Exception(f"Falha ao interpretar JSON. Saída bruta: '{raw_out[:200]}'")

            if isinstance(data, dict) and "error" in data:
                raise Exception(f"Erro interno do Ookla CLI: {data.get('error')}")

            # Conversão: Bytes/s para Mbps
            dl_bytes_sec = data.get('download', {}).get('bandwidth', 0)
            ul_bytes_sec = data.get('upload', {}).get('bandwidth', 0)
            ping_ms = data.get('ping', {}).get('latency', 0)

            result_data['download_speed_mbps'] = round((dl_bytes_sec * 8) / 1000000, 2)
            result_data['upload_speed_mbps'] = round((ul_bytes_sec * 8) / 1000000, 2)
            result_data['latency_ms'] = round(ping_ms, 2)
            
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
