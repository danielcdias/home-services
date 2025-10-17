from decimal import Decimal
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class InternetProvider(models.Model):
    name = models.CharField(max_length=255, unique=True)
    enabled = models.BooleanField(default=True)
    status_check_interval = models.IntegerField(
        null=False,
        help_text="Interval in minutes to check the connection status")
    speed_test_interval = models.IntegerField(
        null=False,
        help_text="Interval in minutes to perform speed tests")
    mininum_hosts_to_ping = models.IntegerField(
        null=False,
        help_text="Minimum number of hosts to ping for status checks", default=3)
    status_ping_error_unstable_threshold = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.3,
        validators=[
            MinValueValidator(Decimal('0.00')),  # Minimum allowed value
            MaxValueValidator(Decimal('1.00'))  # Maximum allowed value
        ],
        null=False,
        help_text="Percentage of hosts with ping error to mark connection as unstable")
    status_ping_error_disconnected_threshold = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.7,
        validators=[
            MinValueValidator(Decimal('0.00')),  # Minimum allowed value
            MaxValueValidator(Decimal('1.00'))  # Maximum allowed value
        ],
        null=False,
        help_text="Percentage of hosts with ping error to mark connection as disconnected")
    status_ping_success_connected_threshold = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.8,
        validators=[
            MinValueValidator(Decimal('0.00')),  # Minimum allowed value
            MaxValueValidator(Decimal('1.00'))  # Maximum allowed value
        ],
        null=False,
        help_text="Percentage of hosts with successful ping to mark connection as connected")
    download_speed_minimun_threshold = models.FloatField(
        validators=[
            MinValueValidator(1.0),  # Minimum allowed value
            MaxValueValidator(10000.0)  # Maximum allowed value
        ],
        null=False,
        help_text="Minimum acceptable download speed in Mbps")
    download_speed_expected_threshold = models.FloatField(
        validators=[
            MinValueValidator(1.0),  # Minimum allowed value
            MaxValueValidator(10000.0)  # Maximum allowed value
        ],
        null=False,
        help_text="Expected download speed in Mbps")
    upload_speed_minimum_threshold = models.FloatField(
        validators=[
            MinValueValidator(1.0),  # Minimum allowed value
            MaxValueValidator(10000.0)  # Maximum allowed value
        ],
        null=False,
        help_text="Minimum acceptable upload speed in Mbps")
    upload_speed_expected_threshold = models.FloatField(
        validators=[
            MinValueValidator(1.0),  # Minimum allowed value
            MaxValueValidator(10000.0)  # Maximum allowed value
        ],
        null=False,
        help_text="Expected upload speed in Mbps")
    id_provider_speedtest = models.CharField(
        max_length=255, null=True, blank=True,
        help_text="Provider ID for speedtest.net (if applicable). https://williamyaps.github.io/wlmjavascript/servercli.html")

    def __str__(self):
        return self.name


class HostsToPing(models.Model):
    name = models.CharField(max_length=255, unique=True)
    hostname_or_ipaddress = models.CharField(
        max_length=255, unique=True, help_text="Hostname or IP address to ping")
    enabled = models.BooleanField(default=True)
    provider = models.ForeignKey(
        InternetProvider, on_delete=models.CASCADE, related_name='hosts_to_ping')

    def __str__(self):
        return f"{self.hostname_or_ipaddress} ({'Enabled' if self.enabled else 'Disabled'})"


class StatusChoices(models.TextChoices):
    CONNECTED = 'connected', 'Connected'
    DISCONNECTED = 'disconnected', 'Disconnected'
    UNSTABLE = 'unstable', 'Unstable'
    UNKNOWN = 'unknown', 'Unknown'


class ConnectionStatus(models.Model):

    status = models.CharField(
        max_length=20, choices=StatusChoices, default='unknown')
    last_checked = models.DateTimeField(auto_now=True)
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
    last_tested = models.DateTimeField(auto_now=True)
    full_results = models.JSONField(
        help_text="Full results from the speed test")
    provider = models.ForeignKey(
        InternetProvider, on_delete=models.CASCADE, related_name='connection_speeds')

    def __str__(self):
        return f"Download: {self.download_speed} Mbps, Upload: {self.upload_speed} Mbps, Ping: {self.ping} ms (Last tested: {self.last_tested})"
