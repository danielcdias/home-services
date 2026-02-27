from django.contrib import admin
from .models import InternetProvider, HostsToPing

# ==========================================
# Configuração Inline para os Hosts
# Permite editar os hosts dentro da página do Provider
# ==========================================


class HostsToPingInline(admin.TabularInline):
    model = HostsToPing
    extra = 1  # Número de linhas em branco extras para adicionar novos hosts rapidamente
    # fields = ('name', 'address', 'enabled') # Descomente e ajuste conforme os campos reais do seu modelo

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
        'contracted_upload_speed'
    )

    # Filtros laterais
    list_filter = ('enabled',)

    # Barra de pesquisa
    search_fields = ('name',)

    # Adiciona a grelha de hosts para edição rápida na mesma página
    inlines = [HostsToPingInline]

# ==========================================
# Configuração dos Hosts de Ping (Página Individual)
# ==========================================


@admin.register(HostsToPing)
class HostsToPingAdmin(admin.ModelAdmin):
    # Ajuste 'address' ou 'host' para o nome correto da coluna no seu model
    list_display = ('id', 'name', 'provider')

    # Filtro lateral para encontrar hosts de um provedor específico
    list_filter = ('provider',)

    ordering = ('id',)

    # search_fields = ('address',) # Descomente se tiver um campo de texto para pesquisar o IP/URL
