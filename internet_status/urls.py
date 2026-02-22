from django.urls import path

from . import views


app_name = 'internet_status'

urlpatterns = [
    path('provider/<int:provider_id>/', views.provider_details, name='details'),
]
