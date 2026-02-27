from django.urls import path

from . import views


app_name = 'internet_status'

urlpatterns = [
    path('provider/<int:provider_id>/',
         views.provider_details, name='details'),
    path('provider/<int:provider_id>/yearly/',
         views.provider_yearly_summary, name='yearly_summary'),
]
