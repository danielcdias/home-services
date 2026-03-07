from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.utils.timezone import localtime
from django.utils import timezone
from django.http import HttpRequest, HttpResponse
from typing import Any
import datetime

from .models import InternetProvider, StatusChoices


def format_duration(td: datetime.timedelta) -> str:
    """Formata um timedelta num texto amigável de horas, minutos e segundos."""
    total_seconds: int = int(td.total_seconds())
    if total_seconds <= 0:
        return "Menos de 1s"
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


@login_required
def provider_details(request: HttpRequest, provider_id: Any) -> HttpResponse:
    provider: InternetProvider = get_object_or_404(
        InternetProvider, id=provider_id, enabled=True)
    contracted_down: float = float(provider.contracted_download_speed)
    contracted_up: float = float(provider.contracted_upload_speed)

    # --- 1. CONFIGURAÇÃO DO FILTRO DE MÊS GLOBAL ---
    available_dates = provider.connection_speeds.dates(
        'last_tested', 'month', order='DESC')
    if not available_dates:
        available_dates = [timezone.now().date().replace(day=1)]

    try:
        selected_month: int = int(
            request.GET.get('month', timezone.now().month))
        selected_year: int = int(request.GET.get('year', timezone.now().year))
    except ValueError:
        selected_month: int = timezone.now().month
        selected_year: int = timezone.now().year

    available_months: list[dict[str, Any]] = [
        {'month': d.month, 'year': d.year, 'label': d.strftime('%m/%Y')}
        for d in available_dates
    ]

    selected_label: str = f"{selected_month:02d}/{selected_year}"
    filename_label: str = f"{selected_year}_{selected_month:02d}"

    # --- 2. FILTRAGEM DOS DADOS DO MÊS ---
    monthly_speeds = provider.connection_speeds.filter(
        last_tested__year=selected_year, last_tested__month=selected_month
    ).order_by('-last_tested')

    monthly_pings = provider.connection_statuses.filter(
        last_checked__year=selected_year, last_checked__month=selected_month
    )

    # --- 3. CONSTRUTOR DE EVENTOS DE INSTABILIDADE (DURAÇÃO) ---
    pings_asc = list(monthly_pings.order_by('last_checked'))
    events: list[dict[str, Any]] = []
    current_event: dict[str, Any] | None = None

    for p in pings_asc:
        if p.status != StatusChoices.CONNECTED:
            if current_event is None or current_event['status'] != p.status:
                if current_event is not None:
                    current_event['end'] = localtime(p.last_checked)
                    current_event['duration'] = format_duration(
                        current_event['end'] - current_event['start'])
                    events.append(current_event)

                current_event = {
                    'status': p.status,
                    'start': localtime(p.last_checked),
                    'end': None,
                    'duration': None,
                    'reason': p.ping_results.get('thresholds', {}).get('reason', '')
                }
        else:
            if current_event is not None:
                current_event['end'] = localtime(p.last_checked)
                current_event['duration'] = format_duration(
                    current_event['end'] - current_event['start'])
                events.append(current_event)
                current_event = None

    if current_event is not None:
        current_event['end'] = localtime(timezone.now())
        current_event['duration'] = format_duration(
            current_event['end'] - current_event['start']) + " (Atual)"
        events.append(current_event)

    events.reverse()

    # --- 4. PREPARAÇÃO DA GRELHA DE HISTÓRICO DE PINGS ---
    monthly_pings_list: list[Any] = list(
        monthly_pings.order_by('-last_checked'))
    for ping in monthly_pings_list:
        try:
            calc = ping.ping_results.get(
                'thresholds', {}).get('calculation', {})
            ping.success_rate_pct = calc.get('success_rate', 0) * 100
            ping.successful_pings = calc.get('successful_pings', 0)
            ping.total_hosts = calc.get('total_hosts', 0)
        except (AttributeError, KeyError, TypeError):
            ping.success_rate_pct = 0
            ping.successful_pings = 0
            ping.total_hosts = 0

    # --- 5. AGRUPAMENTO DIÁRIO PARA OS GRÁFICOS (BARRAS EMPILHADAS) ---
    daily_stats: dict[Any, dict[str, Any]] = {}

    for speed in monthly_speeds:
        d = localtime(speed.last_tested).date()
        if d not in daily_stats:
            daily_stats[d] = {'downloads': [], 'uploads': [], 'statuses': []}
        daily_stats[d]['downloads'].append(speed.download_speed)
        daily_stats[d]['uploads'].append(speed.upload_speed)

    for ping in monthly_pings_list:
        d = localtime(ping.last_checked).date()
        if d not in daily_stats:
            daily_stats[d] = {'downloads': [], 'uploads': [], 'statuses': []}
        daily_stats[d]['statuses'].append(ping.status)

    daily_labels: list[str] = []
    daily_down: list[float] = []
    daily_up: list[float] = []

    daily_down_achieved_pct: list[float] = []
    daily_down_not_achieved_pct: list[float] = []
    daily_up_achieved_pct: list[float] = []
    daily_up_not_achieved_pct: list[float] = []

    daily_conn_pct: list[float] = []
    daily_unst_pct: list[float] = []
    daily_disc_pct: list[float] = []

    for d in sorted(daily_stats.keys()):
        daily_labels.append(d.strftime('%d/%m/%Y'))
        downs = daily_stats[d]['downloads']
        ups = daily_stats[d]['uploads']
        statuses = daily_stats[d]['statuses']

        daily_down.append(round(sum(downs) / len(downs), 2) if downs else 0)
        daily_up.append(round(sum(ups) / len(ups), 2) if ups else 0)

        # Lógica de Cumprimento de Velocidade Diária: Separado Down e Up
        if downs:
            achieved_down: int = sum(
                1 for down in downs if float(down) >= contracted_down)
            total_downs: int = len(downs)
            daily_down_achieved_pct.append(
                round((achieved_down / total_downs) * 100, 2))
            daily_down_not_achieved_pct.append(
                round(((total_downs - achieved_down) / total_downs) * 100, 2))
        else:
            daily_down_achieved_pct.append(0)
            daily_down_not_achieved_pct.append(0)

        if ups:
            achieved_up: int = sum(
                1 for up in ups if float(up) >= contracted_up)
            total_ups: int = len(ups)
            daily_up_achieved_pct.append(
                round((achieved_up / total_ups) * 100, 2))
            daily_up_not_achieved_pct.append(
                round(((total_ups - achieved_up) / total_ups) * 100, 2))
        else:
            daily_up_achieved_pct.append(0)
            daily_up_not_achieved_pct.append(0)

        # Lógica de Estabilidade Diária (Empilhada por Status)
        if statuses:
            total_pings: int = len(statuses)
            conn: int = statuses.count(StatusChoices.CONNECTED)
            unst: int = statuses.count(StatusChoices.UNSTABLE)
            disc: int = statuses.count(StatusChoices.DISCONNECTED)
            daily_conn_pct.append(round((conn / total_pings) * 100, 2))
            daily_unst_pct.append(round((unst / total_pings) * 100, 2))
            daily_disc_pct.append(round((disc / total_pings) * 100, 2))
        else:
            daily_conn_pct.append(0)
            daily_unst_pct.append(0)
            daily_disc_pct.append(0)

    context: dict[str, Any] = {
        'provider': provider,
        'contracted_down': contracted_down,
        'contracted_up': contracted_up,
        'available_months': available_months,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'selected_label': selected_label,
        'filename_label': filename_label,

        'daily_labels': daily_labels,
        'daily_down': daily_down,
        'daily_up': daily_up,
        'daily_down_achieved_pct': daily_down_achieved_pct,
        'daily_down_not_achieved_pct': daily_down_not_achieved_pct,
        'daily_up_achieved_pct': daily_up_achieved_pct,
        'daily_up_not_achieved_pct': daily_up_not_achieved_pct,
        'daily_conn_pct': daily_conn_pct,
        'daily_unst_pct': daily_unst_pct,
        'daily_disc_pct': daily_disc_pct,

        'events': events,
        'monthly_speeds': monthly_speeds,
        'monthly_pings_list': monthly_pings_list,
    }

    return render(request, 'internet_status/details.html', context)


@login_required
def provider_yearly_summary(request: HttpRequest, provider_id: Any) -> HttpResponse:
    provider: InternetProvider = get_object_or_404(
        InternetProvider, id=provider_id, enabled=True)
    contracted_down: float = float(provider.contracted_download_speed)
    contracted_up: float = float(provider.contracted_upload_speed)

    available_dates = provider.connection_speeds.dates(
        'last_tested', 'year', order='DESC')
    if not available_dates:
        available_dates = [timezone.now().date().replace(month=1, day=1)]

    try:
        selected_year: int = int(request.GET.get('year', timezone.now().year))
    except ValueError:
        selected_year: int = timezone.now().year

    available_years: list[int] = [d.year for d in available_dates]

    yearly_speeds = provider.connection_speeds.filter(
        last_tested__year=selected_year)
    yearly_pings = provider.connection_statuses.filter(
        last_checked__year=selected_year)

    monthly_stats: dict[int, dict[str, list[Any]]] = {}
    for m in range(1, 13):
        monthly_stats[m] = {'downloads': [], 'uploads': [], 'statuses': []}

    for speed in yearly_speeds:
        m = localtime(speed.last_tested).month
        monthly_stats[m]['downloads'].append(speed.download_speed)
        monthly_stats[m]['uploads'].append(speed.upload_speed)

    for ping in yearly_pings:
        m = localtime(ping.last_checked).month
        monthly_stats[m]['statuses'].append(ping.status)

    month_labels: list[str] = ['Jan', 'Fev', 'Mar', 'Abr',
                               'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    monthly_down: list[float] = []
    monthly_up: list[float] = []

    monthly_conn_pct: list[float] = []
    monthly_unst_pct: list[float] = []
    monthly_disc_pct: list[float] = []

    monthly_down_achieved_pct: list[float] = []
    monthly_down_not_achieved_pct: list[float] = []
    monthly_up_achieved_pct: list[float] = []
    monthly_up_not_achieved_pct: list[float] = []

    for m in range(1, 13):
        downs = monthly_stats[m]['downloads']
        ups = monthly_stats[m]['uploads']
        statuses = monthly_stats[m]['statuses']

        monthly_down.append(round(sum(downs)/len(downs), 2) if downs else 0)
        monthly_up.append(round(sum(ups)/len(ups), 2) if ups else 0)

        if downs:
            achieved_down: int = sum(
                1 for down in downs if float(down) >= contracted_down)
            total_downs: int = len(downs)
            monthly_down_achieved_pct.append(
                round((achieved_down / total_downs) * 100, 2))
            monthly_down_not_achieved_pct.append(
                round(((total_downs - achieved_down) / total_downs) * 100, 2))
        else:
            monthly_down_achieved_pct.append(0)
            monthly_down_not_achieved_pct.append(0)

        if ups:
            achieved_up: int = sum(
                1 for up in ups if float(up) >= contracted_up)
            total_ups: int = len(ups)
            monthly_up_achieved_pct.append(
                round((achieved_up / total_ups) * 100, 2))
            monthly_up_not_achieved_pct.append(
                round(((total_ups - achieved_up) / total_ups) * 100, 2))
        else:
            monthly_up_achieved_pct.append(0)
            monthly_up_not_achieved_pct.append(0)

        if statuses:
            total_pings: int = len(statuses)
            conn: int = statuses.count(StatusChoices.CONNECTED)
            unst: int = statuses.count(StatusChoices.UNSTABLE)
            disc: int = statuses.count(StatusChoices.DISCONNECTED)
            monthly_conn_pct.append(round((conn / total_pings) * 100, 2))
            monthly_unst_pct.append(round((unst / total_pings) * 100, 2))
            monthly_disc_pct.append(round((disc / total_pings) * 100, 2))
        else:
            monthly_conn_pct.append(0)
            monthly_unst_pct.append(0)
            monthly_disc_pct.append(0)

    context: dict[str, Any] = {
        'provider': provider,
        'contracted_down': contracted_down,
        'contracted_up': contracted_up,
        'available_years': available_years,
        'selected_year': selected_year,
        'month_labels': month_labels,
        'monthly_down': monthly_down,
        'monthly_up': monthly_up,
        'monthly_conn_pct': monthly_conn_pct,
        'monthly_unst_pct': monthly_unst_pct,
        'monthly_disc_pct': monthly_disc_pct,
        'monthly_down_achieved_pct': monthly_down_achieved_pct,
        'monthly_down_not_achieved_pct': monthly_down_not_achieved_pct,
        'monthly_up_achieved_pct': monthly_up_achieved_pct,
        'monthly_up_not_achieved_pct': monthly_up_not_achieved_pct,
    }

    return render(request, 'internet_status/yearly_summary.html', context)
