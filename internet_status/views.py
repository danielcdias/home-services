from datetime import timedelta
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.utils.timezone import localtime
from typing import Any

from .models import InternetProvider, StatusChoices


def provider_details(request: HttpRequest, provider_id: Any) -> HttpResponse:
    provider = get_object_or_404(
        InternetProvider, id=provider_id, enabled=True)

    # --- 1. DADOS RECENTES PARA OS GRÁFICOS DO TOPO ---
    recent_statuses = provider.connection_statuses.order_by(
        '-last_checked')[:50]
    ping_labels = []
    ping_success_rates = []
    for status in reversed(recent_statuses):
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
        horario_local = localtime(speed.last_tested)
        speed_labels.append(horario_local.strftime('%d/%m %H:%M'))
        download_data.append(speed.download_speed)
        upload_data.append(speed.upload_speed)
        latency_data.append(speed.latency)

    recent_failures = provider.connection_statuses.exclude(
        status=StatusChoices.CONNECTED
    ).order_by('-last_checked')[:10]

    # --- 2. DADOS DO RELATÓRIO (MÊS SELECIONADO) ---

    # Identifica os meses que possuem registros de velocidade no banco
    available_dates = provider.connection_speeds.dates(
        'last_tested', 'month', order='DESC')
    if not available_dates:
        available_dates = [timezone.now().date().replace(day=1)]

    # Captura o mês/ano da URL ou define o mais recente por padrão
    try:
        selected_month = int(request.GET.get(
            'month', available_dates[0].month))
        selected_year = int(request.GET.get('year', available_dates[0].year))
    except ValueError:
        selected_month = available_dates[0].month
        selected_year = available_dates[0].year

    # Prepara a lista de opções para o Combo Box do HTML
    available_months = [
        {'month': d.month, 'year': d.year, 'label': d.strftime('%m/%Y')}
        for d in available_dates
    ]

    # Textos formatados para o HTML e para o nome do arquivo JS
    selected_label = f"{selected_month:02d}/{selected_year}"
    filename_label = f"{selected_year}_{selected_month:02d}"

    # Filtra os dados de velocidade e ping para o mês exato selecionado
    monthly_speeds = provider.connection_speeds.filter(
        last_tested__year=selected_year, last_tested__month=selected_month
    )
    monthly_pings = provider.connection_statuses.filter(
        last_checked__year=selected_year, last_checked__month=selected_month
    )

    daily_stats = {}

    # Agrupando velocidades por dia
    for speed in monthly_speeds:
        date_obj = localtime(speed.last_tested).date()
        if date_obj not in daily_stats:
            daily_stats[date_obj] = {
                'downloads': [], 'uploads': [], 'pings': []}
        daily_stats[date_obj]['downloads'].append(speed.download_speed)
        daily_stats[date_obj]['uploads'].append(speed.upload_speed)

    # Agrupando pings por dia
    for ping in monthly_pings:
        date_obj = localtime(ping.last_checked).date()
        if date_obj not in daily_stats:
            daily_stats[date_obj] = {
                'downloads': [], 'uploads': [], 'pings': []}
        try:
            rate = ping.ping_results.get('thresholds', {}).get(
                'calculation', {}).get('success_rate', 0)
            daily_stats[date_obj]['pings'].append(rate * 100)
        except (AttributeError, KeyError, TypeError):
            pass

    monthly_labels = []
    monthly_down = []
    monthly_up = []
    monthly_ping = []
    monthly_table_data = []

    # Calculando as médias diárias do mês
    for d in sorted(daily_stats.keys()):
        label = d.strftime('%d/%m/%Y')
        monthly_labels.append(label)

        downs = daily_stats[d]['downloads']
        ups = daily_stats[d]['uploads']
        pings = daily_stats[d]['pings']

        avg_down = sum(downs) / len(downs) if downs else 0
        avg_up = sum(ups) / len(ups) if ups else 0
        avg_ping = sum(pings) / len(pings) if pings else 0

        monthly_down.append(round(avg_down, 2))
        monthly_up.append(round(avg_up, 2))
        monthly_ping.append(round(avg_ping, 2))

        monthly_table_data.append({
            'date': label,
            'avg_down': round(avg_down, 2),
            'avg_up': round(avg_up, 2),
            'avg_ping': round(avg_ping, 2),
        })

    # Invertendo a tabela para que o dia mais recente do mês fique no topo
    monthly_table_data.reverse()

    context = {
        'provider': provider,
        'recent_failures': recent_failures,
        'ping_labels': ping_labels,
        'ping_success_rates': ping_success_rates,
        'speed_labels': speed_labels,
        'download_data': download_data,
        'upload_data': upload_data,
        'latency_data': latency_data,
        # Variáveis do Relatório Mensal
        'available_months': available_months,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'selected_label': selected_label,
        'filename_label': filename_label,
        'monthly_labels': monthly_labels,
        'monthly_down': monthly_down,
        'monthly_up': monthly_up,
        'monthly_ping': monthly_ping,
        'monthly_table_data': monthly_table_data,
    }

    return render(request, 'internet_status/details.html', context)
