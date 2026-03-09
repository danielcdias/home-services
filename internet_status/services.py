import logging
import ping3
import speedtest
import requests

from typing import Tuple

from core.util import SingletonMeta, log_error
from internet_status.models import InternetProvider, HostsToPing, ConnectionStatus, ConnectionSpeed, StatusChoices

logger = logging.getLogger(__name__)


class InternetCheck(metaclass=SingletonMeta):

    def check_internet_status(self):
        providers: list[InternetProvider] = self._get_hosts()
        for provider in providers:
            status, ping_results = self._ping(provider)
            if not self._save_ping_results(provider, ping_results, status):
                logger.error(
                    f"Erro salvando resultado do ping para provider {provider.name}.")

    def check_internet_speed(self):
        providers: list[InternetProvider] = self._get_hosts()
        for provider in providers:
            speed_results = self._speedtest(provider)
            if not self._save_speed_results(provider, speed_results):
                logger.error(
                    f"Erro salvando resultado do speedtest para provider {provider.name}.")

    def _get_hosts(self) -> list[InternetProvider]:
        result: list[InternetProvider] = []
        try:
            result = InternetProvider.objects.filter(
                enabled=True).prefetch_related('hosts_to_ping')
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
        result_data: dict = {
            'tests_results': [],
            'thresholds': {}
        }
        
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
                'result': 0, # Guardará a latência em ms para ambos os casos
                'success': False,
                'exception': None,
            }

            if host.check_type == 'HTTP':
                http_total += 1
                try:
                    # Timeout curto de 3s. Queremos apenas o cabeçalho 204
                    response = requests.get(host.hostname_or_ipaddress, timeout=3)
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
                        result['result'] = ping_result * 1000 # Convertendo para ms
                        icmp_success += 1
                        total_icmp_latency += result['result']
                    else:
                        result['exception'] = "Timeout"
                except Exception as ex:
                    log_error(logger, "Erro executando ping ICMP.", ex)
                    result['exception'] = str(ex)
                    
            result_data['tests_results'].append(result)

        # === CÁLCULO DAS MÉTRICAS ===
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

        # === MATRIZ DE DECISÃO ===
        
        # Regra 1: Validação Mínima
        if total_hosts < provider.minimum_hosts_to_ping:
            result_status = StatusChoices.UNKNOWN
            result_data['thresholds']['reason'] = f"Apenas {total_hosts} hosts configurados. Mínimo exigido: {provider.minimum_hosts_to_ping}."
            return result_status, result_data

        # Regra 2: HTTP é o Rei (Se HTTP está configurado e todos falharam, a internet caiu, ignoramos o ping)
        if http_total > 0 and http_success == 0:
            result_status = StatusChoices.DISCONNECTED
            result_data['thresholds']['reason'] = "FALHA CRÍTICA: Nenhum teste HTTP 204 obteve sucesso. Possível falha de DNS ou bloqueio na camada 7."
            return result_status, result_data
            
        # Regra 3: Fallback caso o usuário não tenha configurado nenhum HTTP (comportamento legado)
        if http_total == 0 and icmp_total > 0 and icmp_success == 0:
            result_status = StatusChoices.DISCONNECTED
            result_data['thresholds']['reason'] = "FALHA CRÍTICA: 100% de perda de pacotes ICMP (Nenhum teste HTTP configurado)."
            return result_status, result_data

        # Regra 4: Análise de Instabilidade (Degradação de ICMP)
        if icmp_loss_pct >= provider.unstable_packet_loss_threshold:
            result_status = StatusChoices.UNSTABLE
            result_data['thresholds']['reason'] = f"DEGRADAÇÃO: Perda de pacotes ICMP ({icmp_loss_pct:.1f}%) ultrapassou o limite ({provider.unstable_packet_loss_threshold}%)."
        elif avg_icmp_latency >= provider.unstable_latency_threshold:
            result_status = StatusChoices.UNSTABLE
            result_data['thresholds']['reason'] = f"DEGRADAÇÃO: Latência média ICMP ({avg_icmp_latency:.1f}ms) ultrapassou o limite ({provider.unstable_latency_threshold}ms)."
        
        # Regra 5: Conexão Saudável
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

    def _speedtest(self, provider: InternetProvider) -> dict:
        """
        Executa um teste de velocidade usando a biblioteca speedtest-cli.
        """
        result_data = {
            'download_speed_mbps': 0,
            'upload_speed_mbps': 0,
            'latency_ms': 0,
            'test_result': {},
            'thresholds': {
                'provider_config': {
                    'download_speed_minimum_threshold': provider.download_speed_minimum_threshold,
                    'download_speed_expected_threshold': provider.download_speed_expected_threshold,
                    'upload_speed_minimum_threshold': provider.upload_speed_minimum_threshold,
                    'upload_speed_expected_threshold': provider.upload_speed_expected_threshold,
                }
            },
            'exception': None,
        }

        try:
            # CORREÇÃO: Forçar conexão segura (HTTPS) para evitar bloqueios da API Ookla
            st = speedtest.Speedtest(secure=True)
            
            if provider.id_provider_speedtest:
                try:
                    # Garantir que o ID seja passado como inteiro dentro da lista
                    st.get_servers(servers=[int(provider.id_provider_speedtest)])
                except (speedtest.NoMatchedServers, ValueError):
                    logger.warning(f"Servidor Speedtest ID {provider.id_provider_speedtest} não encontrado ou inválido. Usando fallback automático.")
                    st.get_servers()
            else:
                st.get_servers()
                
            try:
                st.get_best_server()
            except speedtest.SpeedtestBestServerFailure:
                # Se a lista de servidores vier vazia da Ookla, falha graciosamente
                raise Exception("A Ookla recusou a conexão ou não retornou servidores válidos na sua região no momento.")

            st.download()
            st.upload()
            test_results = st.results.dict()

            result_data['test_result'] = test_results

            if test_results.get('download'):
                result_data['download_speed_mbps'] = round(
                    test_results['download'] / 1_000_000, 2)

            if test_results.get('upload'):
                result_data['upload_speed_mbps'] = round(
                    test_results['upload'] / 1_000_000, 2)

            if test_results.get('ping'):
                result_data['latency_ms'] = round(test_results['ping'], 2)

        except Exception as ex:
            log_error(
                logger, f"Erro executando speedtest para o provider {provider.name}.", ex)
            result_data['exception'] = str(ex)

        return result_data

    def check_single_status(self, provider: InternetProvider):
        status, ping_results = self._ping(provider)
        if not self._save_ping_results(provider, ping_results, status):
            logger.error(
                f"Erro salvando resultado do ping para provider {provider.name}.")

    def check_single_speed(self, provider: InternetProvider):
        speed_results = self._speedtest(provider)
        if not self._save_speed_results(provider, speed_results):
            logger.error(
                f"Erro salvando resultado do speedtest para provider {provider.name}.")
