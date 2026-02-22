from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from internet_status.models import InternetProvider


def dashboard_view(request: HttpRequest) -> HttpResponse:
    providers = InternetProvider.objects.filter(enabled=True)
    provider_data = []

    # Mapeamento de status para as classes de cor do Bootstrap
    status_colors = {
        'connected': 'success',
        'disconnected': 'danger',
        'unstable': 'warning',
        'unknown': 'secondary'
    }

    # Mapeamento para tradução na tela
    status_labels = {
        'connected': 'Conectado',
        'disconnected': 'Desconectado',
        'unstable': 'Instável',
        'unknown': 'Desconhecido'
    }

    for provider in providers:
        # Pega o último status (ping) e a última velocidade registrados
        latest_status = provider.connection_statuses.order_by(
            '-last_checked').first()
        latest_speed = provider.connection_speeds.order_by(
            '-last_tested').first()

        # Define valores padrão caso ainda não haja testes no banco
        current_status = latest_status.status if latest_status else 'unknown'

        provider_data.append({
            'provider': provider,
            'latest_status': latest_status,
            'latest_speed': latest_speed,
            'color_class': status_colors.get(current_status, 'secondary'),
            'status_label': status_labels.get(current_status, 'Sem dados'),
        })

    context = {
        'provider_data': provider_data,
    }

    return render(request, 'core/dashboard.html', context)
