from django.urls import path
from . import views

app_name = 'internet_status'  # Optional: set an app_name for namespacing

urlpatterns = [
    path('', views.index, name='index'),
]
