from django.urls import path
from . import views

app_name = 'core'  # Optional: set an app_name for namespacing

urlpatterns = [
    path('', views.index, name='index'),
]
