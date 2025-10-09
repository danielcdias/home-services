from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('', include('core.urls')),
    path('admin/', admin.site.urls),
    path('internet_status/', include('internet_status.urls'),)
]
