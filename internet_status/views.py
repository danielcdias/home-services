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
    min_down: float = float(provider.download_speed_minimum_threshold)
    min_up: float = float(provider.upload_speed_minimum_threshold)

    # --- 1. CONFIGURAÇÃO DO PERÍODO ---
    # Obtém anos disponíveis baseados nos testes de velocidade
    years_qs = provider.connection_speeds.dates('last_tested', 'year')
    available_years: list[int] = [d.year for d in years_qs]
    
    current_year: int = timezone.now().year
    current_month: int = timezone.now().month

    if current_year not in available_years:
        available_years.append(current_year)
    available_years.sort(reverse=True)

    try:
        selected_year: int = int(request.GET.get('year', current_year))
    except ValueError:
        selected_year = current_year

    if selected_year not in available_years:
        selected_year = available_years[0] if available_years else current_year

    # Obtém meses disponíveis *para o ano selecionado*
    months_qs = provider.connection_speeds.filter(
        last_tested__year=selected_year).dates('last_tested', 'month')
    available_months_ints: list[int] = [d.month for d in months_qs]

    if selected_year == current_year and current_month not in available_months_ints:
        available_months_ints.append(current_month)

    available_months_ints.sort()

    MONTH_NAMES: list[str] = [
        "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    available_months: list[dict[str, Any]] = [
        {'month': m, 'year': selected_year, 'label': f"{MONTH_NAMES[m]} {selected_year}"}
        for m in available_months_ints
    ]

    # Determina o mês a exibir
    try:
        selected_month_req = request.GET.get('month')
        if selected_month_req:
            selected_month = int(selected_month_req)
        else:
            selected_month = current_month if selected_year == current_year else (
                available_months_ints[-1] if available_months_ints else current_month)
    except ValueError:
        selected_month = current_month

    if available_months_ints and selected_month not in available_months_ints:
         selected_month = available_months_ints[-1]

    selected_label: str = f"{MONTH_NAMES[selected_month]} {selected_year}"
    filename_label: str = f"{MONTH_NAMES[selected_month]}_{selected_year}"

    # --- 2. CONSULTAS BASE PARA O MÊS SELECIONADO ---
    monthly_speeds_qs = provider.connection_speeds.filter(
        last_tested__year=selected_year, last_tested__month=selected_month
    ).order_by('-last_tested')
    
    monthly_pings_qs = provider.connection_statuses.filter(
        last_checked__year=selected_year, last_checked__month=selected_month
    ).order_by('-last_checked')

    # Convertendo para lista para usar em Python (cálculos) e no template
    monthly_speeds = list(monthly_speeds_qs)
    monthly_pings = list(monthly_pings_qs)

    # --- 3. DADOS PARA O GRÁFICO (AGRUPADOS POR DIA) ---
    import calendar
    _, num_days = calendar.monthrange(selected_year, selected_month)
    
    daily_labels: list[int] = list(range(1, num_days + 1))
    
    daily_down: list[float] = [0.0] * num_days
    daily_up: list[float] = [0.0] * num_days
    daily_speed_counts: list[int] = [0] * num_days

    daily_down_achieved_counts: list[int] = [0] * num_days
    daily_up_achieved_counts: list[int] = [0] * num_days
    
    # Preenchimento de Velocidades
    for speed in monthly_speeds:
        day: int = localtime(speed.last_tested).day
        idx: int = day - 1
        daily_down[idx] += speed.download_speed
        daily_up[idx] += speed.upload_speed
        daily_speed_counts[idx] += 1
        
        if speed.download_speed >= contracted_down:
            daily_down_achieved_counts[idx] += 1
        if speed.upload_speed >= contracted_up:
            daily_up_achieved_counts[idx] += 1

    # Médias diárias de velocidade e percentuais de cumprimento
    daily_down_achieved_pct: list[float] = []
    daily_down_not_achieved_pct: list[float] = []
    daily_up_achieved_pct: list[float] = []
    daily_up_not_achieved_pct: list[float] = []

    for i in range(num_days):
        count = daily_speed_counts[i]
        if count > 0:
            daily_down[i] = round(daily_down[i] / count, 2)
            daily_up[i] = round(daily_up[i] / count, 2)
            
            down_pct = (daily_down_achieved_counts[i] / count) * 100
            up_pct = (daily_up_achieved_counts[i] / count) * 100
            
            daily_down_achieved_pct.append(round(down_pct, 1))
            daily_down_not_achieved_pct.append(round(100 - down_pct, 1))
            daily_up_achieved_pct.append(round(up_pct, 1))
            daily_up_not_achieved_pct.append(round(100 - up_pct, 1))
        else:
            daily_down_achieved_pct.append(0.0)
            daily_down_not_achieved_pct.append(0.0)
            daily_up_achieved_pct.append(0.0)
            daily_up_not_achieved_pct.append(0.0)

    # Preenchimento de Ping/Status (Contagens diárias)
    daily_ping_counts: list[int] = [0] * num_days
    daily_conn_counts: list[int] = [0] * num_days
    daily_unst_counts: list[int] = [0] * num_days
    daily_disc_counts: list[int] = [0] * num_days

    for ping in monthly_pings:
        day = localtime(ping.last_checked).day
        idx = day - 1
        daily_ping_counts[idx] += 1
        
        if ping.status == StatusChoices.CONNECTED:
             daily_conn_counts[idx] += 1
        elif ping.status == StatusChoices.UNSTABLE:
             daily_unst_counts[idx] += 1
        elif ping.status == StatusChoices.DISCONNECTED:
             daily_disc_counts[idx] += 1

    daily_conn_pct: list[float] = []
    daily_unst_pct: list[float] = []
    daily_disc_pct: list[float] = []

    for i in range(num_days):
        total = daily_ping_counts[i]
        if total > 0:
            daily_conn_pct.append(round((daily_conn_counts[i] / total) * 100, 1))
            daily_unst_pct.append(round((daily_unst_counts[i] / total) * 100, 1))
            daily_disc_pct.append(round((daily_disc_counts[i] / total) * 100, 1))
        else:
             daily_conn_pct.append(0.0)
             daily_unst_pct.append(0.0)
             daily_disc_pct.append(0.0)

    # --- 4. IDENTIFICAÇÃO DE EVENTOS DE INSTABILIDADE / QUEDA ---
    # Para calcular a duração, os eventos precisam estar em ordem cronológica (crescente)
    pings_asc = list(reversed(monthly_pings))
    events: list[dict] = []
    current_event: dict | None = None

    for ping in pings_asc:
        if ping.status in [StatusChoices.DISCONNECTED, StatusChoices.UNSTABLE]:
            if current_event is None:
                # Inicia um novo evento
                reason_str = ""
                if isinstance(ping.ping_results, dict):
                    thresholds = ping.ping_results.get('thresholds', {})
                    reason_str = thresholds.get('reason', '')
                current_event = {
                    'start': ping.last_checked,
                    'end': ping.last_checked,
                    'status': ping.status,
                    'reason': reason_str
                }
            else:
                # Se o status mudar (ex: UNSTABLE -> DISCONNECTED), fecha o evento atual e abre outro
                if current_event['status'] != ping.status:
                     events.insert(0, {
                        'start': current_event['start'],
                        'end': current_event['end'],
                        'duration': format_duration(current_event['end'] - current_event['start']),
                        'status': current_event['status'],
                        'reason': current_event['reason']
                     })
                     reason_str = ""
                     if isinstance(ping.ping_results, dict):
                        thresholds = ping.ping_results.get('thresholds', {})
                        reason_str = thresholds.get('reason', '')
                     current_event = {
                        'start': ping.last_checked,
                        'end': ping.last_checked,
                        'status': ping.status,
                        'reason': reason_str
                     }
                else:
                    # Continua o mesmo evento, atualiza o tempo final
                    current_event['end'] = ping.last_checked
        else:
            # Status CONNECTED: se havia um evento aberto, fecha-o
            if current_event is not None:
                events.insert(0, {
                    'start': current_event['start'],
                    'end': current_event['end'],
                    'duration': format_duration(current_event['end'] - current_event['start']),
                    'status': current_event['status'],
                    'reason': current_event['reason']
                })
                current_event = None

    # Se ao final do mês ainda houver um evento aberto
    if current_event is not None:
        events.insert(0, {
            'start': current_event['start'],
            'end': current_event['end'],
            'duration': format_duration(current_event['end'] - current_event['start']),
            'status': current_event['status'],
            'reason': current_event['reason']
        })

    # --- 5. ENRIQUECER LISTA DE PINGS PARA A TABELA (Trazendo o Sucesso %) ---
    # Vamos manter a lista para exibir, com alguns pré-cálculos para facilitar no template
    for ping in monthly_pings:
        ping.success_rate_pct = 0
        ping.successful_pings = 0
        ping.total_hosts = 0
        if isinstance(ping.ping_results, dict):
             results = ping.ping_results.get('tests_results', [])
             ping.total_hosts = len(results)
             ping.successful_pings = sum(1 for r in results if r.get('success') is True)
             if ping.total_hosts > 0:
                 ping.success_rate_pct = (ping.successful_pings / ping.total_hosts) * 100

    context: dict[str, Any] = {
        'provider': provider,
        'contracted_down': contracted_down,
        'contracted_up': contracted_up,
        'min_down': min_down,
        'min_up': min_up,
        'available_years': available_years,
        'selected_year': selected_year,
        'available_months': available_months,
        'selected_month': selected_month,
        'selected_label': selected_label,
        'filename_label': filename_label,
        
        # Dados para os Gráficos
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
        
        # Dados para as Tabelas
        'monthly_speeds': monthly_speeds,
        'monthly_pings_list': monthly_pings, # usando a lista enriquecida
        'events': events,
    }

    return render(request, 'internet_status/details.html', context)


@login_required
def provider_yearly_summary(request: HttpRequest, provider_id: Any) -> HttpResponse:
    provider: InternetProvider = get_object_or_404(
        InternetProvider, id=provider_id, enabled=True)
    contracted_down: float = float(provider.contracted_download_speed)
    contracted_up: float = float(provider.contracted_upload_speed)
    min_down: float = float(provider.download_speed_minimum_threshold)
    min_up: float = float(provider.upload_speed_minimum_threshold)

    years_qs = provider.connection_speeds.dates('last_tested', 'year')
    available_years: list[int] = [d.year for d in years_qs]
    current_year: int = timezone.now().year

    if current_year not in available_years:
        available_years.append(current_year)
    available_years.sort(reverse=True)

    try:
        selected_year: int = int(request.GET.get('year', current_year))
    except ValueError:
        selected_year = current_year

    if selected_year not in available_years:
        selected_year = available_years[0] if available_years else current_year

    MONTH_NAMES: list[str] = [
        "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
        "Jul", "Ago", "Set", "Out", "Nov", "Dez"
    ]
    month_labels: list[str] = MONTH_NAMES

    monthly_down: list[float] = []
    monthly_up: list[float] = []
    
    monthly_down_achieved_pct: list[float] = []
    monthly_down_not_achieved_pct: list[float] = []
    monthly_up_achieved_pct: list[float] = []
    monthly_up_not_achieved_pct: list[float] = []

    monthly_conn_pct: list[float] = []
    monthly_unst_pct: list[float] = []
    monthly_disc_pct: list[float] = []

    for month in range(1, 13):
        speeds = provider.connection_speeds.filter(
            last_tested__year=selected_year, last_tested__month=month)
        
        if speeds:
            total_speeds: int = speeds.count()
            avg_down: float = round(sum(s.download_speed for s in speeds) / total_speeds, 2)
            avg_up: float = round(sum(s.upload_speed for s in speeds) / total_speeds, 2)
            monthly_down.append(avg_down)
            monthly_up.append(avg_up)

            down_achieved: int = sum(1 for s in speeds if s.download_speed >= contracted_down)
            up_achieved: int = sum(1 for s in speeds if s.upload_speed >= contracted_up)
            
            d_pct: float = (down_achieved / total_speeds) * 100
            u_pct: float = (up_achieved / total_speeds) * 100
            
            monthly_down_achieved_pct.append(round(d_pct, 1))
            monthly_down_not_achieved_pct.append(round(100 - d_pct, 1))
            monthly_up_achieved_pct.append(round(u_pct, 1))
            monthly_up_not_achieved_pct.append(round(100 - u_pct, 1))
        else:
            monthly_down.append(0)
            monthly_up.append(0)
            monthly_down_achieved_pct.append(0)
            monthly_down_not_achieved_pct.append(0)
            monthly_up_achieved_pct.append(0)
            monthly_up_not_achieved_pct.append(0)

        statuses_qs = provider.connection_statuses.filter(
            last_checked__year=selected_year, last_checked__month=month).values_list('status', flat=True)
        statuses: list[str] = list(statuses_qs)

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
        'min_down': min_down,
        'min_up': min_up,
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
