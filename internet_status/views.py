from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils.timezone import localtime
from typing import Any

from .models import InternetProvider, StatusChoices


def provider_details(request: HttpRequest, provider_id: Any) -> HttpResponse:
    provider = get_object_or_404(
        InternetProvider, id=provider_id, enabled=True)

    recent_statuses = provider.connection_statuses.order_by(
        '-last_checked')[:50]

    ping_labels = []
    ping_success_rates = []

    for status in reversed(recent_statuses):
        # 2. Converte para o horário local antes de formatar
        horario_local = localtime(status.last_checked)
        ping_labels.append(horario_local.strftime('%H:%M'))

        try:
            rate = status.ping_results.get('thresholds', {}).get(
                'calculation', {}).get('success_rate', 0)
            ping_success_rates.append(rate * 100)
        except (AttributeError, KeyError, TypeError):
            ping_success_rates.append(0)

    recent_speeds = provider.connection_speeds.order_by('-last_tested')[:24]

    speed_labels = []
    download_data = []
    upload_data = []
    latency_data = []

    for speed in reversed(recent_speeds):
        # 3. Faz o mesmo para os labels de velocidade
        horario_local = localtime(speed.last_tested)
        speed_labels.append(horario_local.strftime('%d/%m %H:%M'))

        download_data.append(speed.download_speed)
        upload_data.append(speed.upload_speed)
        latency_data.append(speed.latency)

    recent_failures = provider.connection_statuses.exclude(
        status=StatusChoices.CONNECTED
    ).order_by('-last_checked')[:10]

    context = {
        'provider': provider,
        'recent_failures': recent_failures,
        'ping_labels': ping_labels,
        'ping_success_rates': ping_success_rates,
        'speed_labels': speed_labels,
        'download_data': download_data,
        'upload_data': upload_data,
        'latency_data': latency_data,
    }

    return render(request, 'internet_status/details.html', context)
