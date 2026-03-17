from django.urls import path
from . import views

urlpatterns = [
    path('', views.export_excel, name='export_excel'),
]