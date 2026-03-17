from django.urls import path
from . import views

urlpatterns = [
    path('',                 views.employee_list,   name='employee_list'),
    path('add/',             views.employee_create, name='employee_create'),
    path('<int:pk>/edit/',   views.employee_edit,   name='employee_edit'),
    path('<int:pk>/delete/', views.employee_delete, name='employee_delete'),
]
