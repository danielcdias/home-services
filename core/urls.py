from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Rota pública principal (Portfólio / Apresentação)
    path('', views.index_view, name='index'),
    # Rota do sistema (Painel de Monitoramento)
    path('dashboard/', views.dashboard_view, name='dashboard'),
]
