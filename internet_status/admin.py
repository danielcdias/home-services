from django.contrib import admin
from .models import InternetProvider, HostsToPing

# ==========================================
# Configuração Inline para os Hosts
# Permite editar os hosts dentro da página do Provider
# ==========================================


class HostsToPingInline(admin.TabularInline):
    model = HostsToPing
    extra = 1  # Número de linhas em branco extras para adicionar novos hosts rapidamente
    fields = ('name', 'hostname_or_ipaddress', 'check_type', 'enabled')


# ==========================================
# Configuração do Provedor de Internet
# ==========================================


@admin.register(InternetProvider)
class InternetProviderAdmin(admin.ModelAdmin):
    # Colunas que aparecerão na lista geral
    list_display = (
        'name',
        'enabled',
        'contracted_download_speed',
        'contracted_upload_speed',
        'status_check_interval',
        'speed_test_interval'
    )

    # Filtros laterais
    list_filter = ('enabled',)

    # Barra de pesquisa
    search_fields = ('name',)

    # Campos apenas de leitura (geridos pelo sistema de alertas)
    readonly_fields = ('speed_alert_active', 'connection_alert_active')

    # Organização visual do formulário em secções (Fieldsets)
    fieldsets = (
        ('Configurações Gerais', {
            'fields': ('name', 'enabled', 'destination_emails')
        }),
        ('Plano Contratado', {
            'fields': ('contracted_download_speed', 'contracted_upload_speed')
        }),
        ('Agendamento de Testes (CRON)', {
            'fields': ('status_check_interval', 'speed_test_interval'),
            'description': 'Utilize expressões CRON para controlo exato (ex: "*/5 * * * *" para a cada 5 minutos).'
        }),
        ('Matriz de Decisão (Conectividade)', {
            'fields': (
                'minimum_hosts_to_ping',
                'unstable_packet_loss_threshold',
                'unstable_latency_threshold',
                'connection_drop_limit'
            ),
            'description': 'Parâmetros de avaliação para testes ICMP (O status HTTP 204 sobrepõe-se sempre de forma absoluta a estes limites para validar conectividade real).'
        }),
        ('Limites e Alertas (Speedtest)', {
            'fields': (
                'id_provider_speedtest',
                'download_speed_expected_threshold',
                'download_speed_minimum_threshold',
                'upload_speed_expected_threshold',
                'upload_speed_minimum_threshold',
                'speed_drop_limit'
            ),
            'description': 'Mantenha o ID do servidor em branco para usar o fallback automático de menor latência da região.'
        }),
        ('Estado dos Alertas (Automático)', {
            'fields': ('speed_alert_active', 'connection_alert_active'),
            'classes': ('collapse',),
            'description': 'Estas flags são controladas automaticamente pelo motor de alertas (db_signals).'
        }),
    )

    # Adiciona a grelha de hosts para edição rápida na mesma página
    inlines = [HostsToPingInline]

# ==========================================
# Configuração dos Hosts de Ping (Página Individual)
# ==========================================


@admin.register(HostsToPing)
class HostsToPingAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'hostname_or_ipaddress', 'check_type', 'provider', 'enabled')

    # Filtros laterais 
    list_filter = ('provider', 'check_type', 'enabled')

    search_fields = ('name', 'hostname_or_ipaddress')
