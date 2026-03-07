from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect

from internet_status.models import InternetProvider


def index_view(request: HttpRequest) -> HttpResponse:
    """
    Renderiza a página inicial pública (Landing Page / Portfólio).
    """
    return render(request, 'core/index.html')


@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    """
    Renderiza o painel de controle interno do Home Services.
    """
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


def custom_logout_view(request: HttpRequest) -> HttpResponse:
    """
    Desconecta o usuário de forma segura e redireciona para a página inicial pública.
    """
    logout(request)
    return redirect('core:index')