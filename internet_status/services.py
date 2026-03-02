import logging
import ping3
import speedtest

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
        hosts_to_ping = HostsToPing.objects.filter(
            provider=provider, enabled=True)
        for host in hosts_to_ping:
            result = {
                'name': host.name,
                'hostname_or_ipaddress': host.hostname_or_ipaddress,
                'result': 0,
                'success': False,
                'exception': None,
            }
            try:
                ping_result = ping3.ping(host.hostname_or_ipaddress)
                if ping_result is not False and ping_result is not None:
                    result['result'] = ping_result
                    result['success'] = True
            except Exception as ex:
                log_error(logger, "Erro executando ping.", ex)
                result['exception'] = str(ex)
            result_data['tests_results'].append(result)

        # Análise dos pings de acordo com os thresholds do provider
        total_hosts = len(result_data['tests_results'])
        successful_pings = sum(
            1 for r in result_data['tests_results'] if r['success'])
        failed_pings = total_hosts - successful_pings

        success_rate = (successful_pings /
                        total_hosts) if total_hosts > 0 else 0
        failure_rate = (failed_pings / total_hosts) if total_hosts > 0 else 0

        # Adiciona informações de cálculo e thresholds ao resultado
        result_data['thresholds'] = {
            'provider_config': {
                'minimum_hosts_to_ping': provider.minimum_hosts_to_ping,
                'status_ping_error_unstable_threshold': float(provider.status_ping_error_unstable_threshold),
                'status_ping_error_disconnected_threshold': float(provider.status_ping_error_disconnected_threshold),
                'status_ping_success_connected_threshold': float(provider.status_ping_success_connected_threshold),
            },
            'calculation': {
                'total_hosts': total_hosts,
                'successful_pings': successful_pings,
                'failed_pings': failed_pings,
                'success_rate': round(success_rate, 2),
                'failure_rate': round(failure_rate, 2),
            },
            'reason': ''
        }

        # Verifica a quantidade mínima de hosts para ping
        if total_hosts < provider.minimum_hosts_to_ping:
            result_status = StatusChoices.UNKNOWN
            result_data['thresholds']['reason'] = (
                f"Número de hosts ({total_hosts}) "
                f"inferior ao mínimo exigido ({provider.minimum_hosts_to_ping})."
            )
            return result_status, result_data

        if success_rate >= float(provider.status_ping_success_connected_threshold):
            result_status = StatusChoices.CONNECTED
            result_data['thresholds']['reason'] = (
                f"Taxa de sucesso ({success_rate:.2f}) atingiu ou superou o "
                f"threshold de conectado ({provider.status_ping_success_connected_threshold})."
            )
        elif failure_rate >= float(provider.status_ping_error_disconnected_threshold):
            result_status = StatusChoices.DISCONNECTED
            result_data['thresholds']['reason'] = (
                f"Taxa de falha ({failure_rate:.2f}) atingiu ou superou o "
                f"threshold de desconectado ({provider.status_ping_error_disconnected_threshold})."
            )
        else:
            # Tudo o que não for perfeito nem crítico será considerado instável,
            # fechando a lacuna de "unknown".
            result_status = StatusChoices.UNSTABLE
            result_data['thresholds']['reason'] = (
                f"A conexão não atingiu os limites de sucesso ({provider.status_ping_success_connected_threshold}) "
                f"nem de desconexão total, registando uma taxa de sucesso de {success_rate:.2f}. Classificada como Instável."
            )

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

        Args:
            provider (InternetProvider): A instância do provedor de internet
                                         com as configurações de threshold.

        Returns:
            dict: Um dicionário contendo as velocidades de download/upload em Mbps,
                  a latência em ms, os resultados completos do teste e os
                  thresholds configurados para o provedor.
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
            st = speedtest.Speedtest()
            try:
                st.get_servers(servers=[provider.id_provider_speedtest])
            except speedtest.NoMatchedServers:
                st.get_servers([])
                st.get_best_server()
            st.download()
            st.upload()
            test_results = st.results.dict()

            result_data['test_result'] = test_results

            # A biblioteca speedtest-cli retorna valores em bits por segundo.
            # Convertendo para megabits por segundo (Mbps) -> valor / 1_000_000
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
