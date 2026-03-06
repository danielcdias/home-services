from django.contrib import admin
from django.urls import path, include
from two_factor.urls import urlpatterns as tf_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    # Rotas de Autenticação 2FA (precisa vir antes das rotas do 'core' para evitar conflitos)
    path('', include(tf_urls)),
    # Rotas do seu ecossistema (Home e Dashboard)
    path('', include('core.urls')),
    path('internet-status/', include('internet_status.urls')),
]
