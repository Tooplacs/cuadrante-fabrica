from django.urls import path
from . import views

urlpatterns = [
    path('',             views.calendar_view,   name='calendar_view'),
    path('generate/',    views.generate_view,   name='generate_schedule'),
    path('edit/<int:pk>/', views.edit_assignment, name='edit_assignment'),
]