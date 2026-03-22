from croniter import croniter
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from geopy.distance import geodesic


def validate_cron_expression(value):
    if not croniter.is_valid(value):
        raise ValidationError(f"'{value}' não é uma expressão CRON válida.")


class InternetProvider(models.Model):
    name = models.CharField(max_length=255, unique=True)
    enabled = models.BooleanField(default=True)
    contracted_download_speed = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.0,
        verbose_name="Download Contratado (Mbps)",
        help_text="Velocidade de download contratada junto à operadora."
    )
    contracted_upload_speed = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.0,
        verbose_name="Upload Contratado (Mbps)",
        help_text="Velocidade de upload contratada junto à operadora."
    )
    status_check_interval = models.CharField(
        max_length=100,
        default='*/5 * * * *',
        validators=[validate_cron_expression],
        verbose_name="Frequência do Ping (CRON)",
        help_text="Ex: '*/5 * * * *' para a cada 5 min."
    )
    speed_test_interval = models.CharField(
        max_length=100,
        default='0 * * * *',
        validators=[validate_cron_expression],
        verbose_name="Frequência do Speedtest (CRON)",
        help_text="Ex: '0 * * * *' para a cada hora exata."
    )
    download_speed_minimum_threshold = models.FloatField(
        validators=[
            MinValueValidator(1.0),  
            MaxValueValidator(10000.0)  
        ],
        null=False,
        help_text="Referência de velocidade de download mínima aceitável in Mbps.")
    upload_speed_minimum_threshold = models.FloatField(
        validators=[
            MinValueValidator(1.0),  
            MaxValueValidator(10000.0)
        ],
        null=False,
        help_text="Referência de velocidade de upload mínima aceitável in Mbps.")
    id_provider_speedtest = models.CharField(
        max_length=255, null=True, blank=True,
        help_text="ID do provedor do speedtest.net (se aplicável). https://williamyaps.github.io/wlmjavascript/servercli.html")
    connection_drop_limit = models.IntegerField(
        default=5,
        verbose_name="Limite de Falhas de Conexão",
        help_text="Número de testes de conectividade consecutivos com falha/instabilidade para disparar alerta."
    )
    speed_drop_limit = models.IntegerField(
        default=3,
        verbose_name="Limite de Quedas de Velocidade",
        help_text="Número de testes de velocidade consecutivos abaixo de 100Mbps para disparar alerta."
    )
    destination_emails = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="E-mails de Destino",
        help_text="Endereços de e-mail que receberão os alertas (separados por vírgula)."
    )
    speed_alert_active = models.BooleanField(
        default=False,
        editable=False,
        verbose_name="Alerta de Velocidade Ativo",
        help_text="Marcado automaticamente quando o alerta é enviado. Desmarcado quando a rede normaliza."
    )
    connection_alert_active = models.BooleanField(
        default=False,
        editable=False,
        verbose_name="Alerta de Conexão Ativo",
        help_text="Marcado automaticamente quando o alerta é enviado. Desmarcado quando a rede normaliza."
    )

    def __str__(self):
        return self.name

    @property
    def destination_emails_list(self):
        if self.destination_emails:
            return [email.strip() for email in self.destination_emails.split(',') if email.strip()]
        return []


class CheckTypeChoices(models.TextChoices):
    ICMP_PING = 'ICMP', 'ICMP Ping'
    HTTP_204 = 'HTTP', 'HTTP 204 (Captive Portal)'


class HostsToPing(models.Model):
    name = models.CharField(max_length=255)
    hostname_or_ipaddress = models.CharField(
        max_length=255, help_text="Hostname/IP (para ICMP) ou URL completa (para HTTP, ex: http://clients3.google.com/generate_204)")
    check_type = models.CharField(
        max_length=4,
        choices=CheckTypeChoices.choices,
        default=CheckTypeChoices.ICMP_PING,
        help_text="Selecione HTTP para URLs de Portal Cativo ou ICMP para pings tradicionais."
    )
    enabled = models.BooleanField(default=True)
    provider = models.ForeignKey(
        InternetProvider, on_delete=models.CASCADE, related_name='hosts_to_ping')

    def __str__(self):
        return f"{self.hostname_or_ipaddress} ({self.check_type}) - {'Ativo' if self.enabled else 'Inativo'}"

    class Meta:
        unique_together = ['provider', 'hostname_or_ipaddress']


class StatusChoices(models.TextChoices):
    CONNECTED = 'connected', 'Connected'
    DISCONNECTED = 'disconnected', 'Disconnected'
    UNSTABLE = 'unstable', 'Unstable'
    UNKNOWN = 'unknown', 'Unknown'


class ConnectionStatus(models.Model):
    status = models.CharField(
        max_length=20, choices=StatusChoices, default='unknown')
    last_checked = models.DateTimeField(auto_now_add=True)
    ping_results = models.JSONField(
        help_text="Ping results for the last check, including hosts with success and error.")
    provider = models.ForeignKey(
        InternetProvider, on_delete=models.CASCADE, related_name='connection_statuses')

    def __str__(self):
        return f"Status: {self.status} (Last checked: {self.last_checked})"


class ConnectionSpeed(models.Model):
    download_speed = models.FloatField(help_text="Download speed in Mbps")
    upload_speed = models.FloatField(help_text="Upload speed in Mbps")
    latency = models.FloatField(help_text="Latency in ms")
    last_tested = models.DateTimeField(auto_now_add=True)
    full_results = models.JSONField(
        help_text="Full results from the speed test")
    provider = models.ForeignKey(
        InternetProvider, on_delete=models.CASCADE, related_name='connection_speeds')

    def __str__(self):
        return f"Download: {self.download_speed} Mbps, Upload: {self.upload_speed} Mbps, Latency: {self.latency} ms (Last tested: {self.last_tested})"

    @property
    def server_distance_km(self):
        try:
            client_data = self.full_results.get('test_result', {}).get('client', {})
            server_data = self.full_results.get('test_result', {}).get('server', {})
            
            client_lat = client_data.get('lat')
            client_lon = client_data.get('lon')
            server_lat = server_data.get('lat')
            server_lon = server_data.get('lon')
            
            if client_lat and client_lon and server_lat and server_lon:
                p1 = (float(client_lat), float(client_lon))
                p2 = (float(server_lat), float(server_lon))
                return round(geodesic(p1, p2).kilometers, 2)
        except (KeyError, TypeError, ValueError):
            return None
        return None


class DailyStatusSummary(models.Model):
    """
    Armazena o resumo diário de conectividade com a distribuição de todos os status.
    """
    provider = models.ForeignKey(
        InternetProvider, on_delete=models.CASCADE, related_name='daily_status_summaries')
    date = models.DateField(db_index=True)
    total_checks = models.IntegerField(help_text="Total de verificações realizadas no dia")
    
    connected_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Percentual de status CONNECTED")
    unstable_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Percentual de status UNSTABLE")
    disconnected_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Percentual de status DISCONNECTED")
    unknown_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Percentual de status UNKNOWN")

    class Meta:
        unique_together = ('provider', 'date')
        verbose_name = "Resumo Diário de Status"
        verbose_name_plural = "Resumos Diários de Status"

    def __str__(self):
        return f"{self.provider.name} - {self.date} (Conectado: {self.connected_pct}%)"


class DailySpeedSummary(models.Model):
    """
    Armazena o resumo diário de velocidades para fins de histórico de longo prazo.
    """
    provider = models.ForeignKey(
        InternetProvider, on_delete=models.CASCADE, related_name='daily_speed_summaries')
    date = models.DateField(db_index=True)
    avg_download = models.FloatField(help_text="Média de download (Mbps) do dia")
    avg_upload = models.FloatField(help_text="Média de upload (Mbps) do dia")
    avg_latency = models.FloatField(help_text="Média de latência (ms) do dia")

    class Meta:
        unique_together = ('provider', 'date')
        verbose_name = "Resumo Diário de Velocidade"
        verbose_name_plural = "Resumos Diários de Velocidade"

    def __str__(self):
        return f"{self.provider.name} - {self.date}: {self.avg_download} Mbps"


class MonthlyInternetSummary(models.Model):
    """
    Armazena indicadores consolidados por mês para performance e histórico.
    """
    provider = models.ForeignKey(
        InternetProvider, on_delete=models.CASCADE, related_name='monthly_summaries')
    year = models.IntegerField()
    month = models.IntegerField()
    avg_connectivity = models.FloatField(help_text="Percentual médio de conectividade")
    avg_download = models.FloatField(help_text="Velocidade média de download (Mbps)")
    avg_upload = models.FloatField(help_text="Velocidade média de upload (Mbps)")
    download_pct_contracted = models.FloatField(help_text="% do download contratado")
    upload_pct_contracted = models.FloatField(help_text="% do upload contratado")

    class Meta:
        unique_together = ('provider', 'year', 'month')
        verbose_name = "Resumo Mensal de Internet"
        verbose_name_plural = "Resumos Mensais de Internet"

    def __str__(self):
        return f"{self.provider.name} - {self.month}/{self.year}"
