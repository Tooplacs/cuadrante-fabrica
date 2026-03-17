from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/',     admin.site.urls),
    path('employees/', include('employees.urls')),
    path('schedule/',  include('schedule.urls')),
    path('export/',    include('export_excel.urls')),
]