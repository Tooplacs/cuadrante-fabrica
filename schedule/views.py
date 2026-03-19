from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import ShiftAssignment
from .scheduler import generate_schedule, get_schedule_for_period
from employees.models import Employee
import datetime


def calendar_view(request):
    today       = datetime.date.today()
    start_year  = int(request.GET.get('start_year', today.year))
    start_month = int(request.GET.get('start_month', today.month))
    employees   = Employee.objects.filter(is_active=True, departamento='produccion')
    period      = get_schedule_for_period(start_year, 1, 12, departamento='produccion')
    return render(request, 'schedule/calendar_view.html', {
        'employees':   employees,
        'period':      period,
        'start_year':  start_year,
        'start_month': start_month,
        'today':       today,
    })


def calendar_acondicionamiento(request):
    today       = datetime.date.today()
    start_year  = int(request.GET.get('start_year', today.year))
    start_month = int(request.GET.get('start_month', today.month))
    employees   = Employee.objects.filter(is_active=True, departamento='acondicionamiento')
    period      = get_schedule_for_period(start_year, 1, 12, departamento='acondicionamiento')
    return render(request, 'schedule/calendar_acondicionamiento.html', {
        'employees':   employees,
        'period':      period,
        'start_year':  start_year,
        'start_month': start_month,
        'today':       today,
    })


def generate_view(request):
    if request.method == 'POST':
        try:
            year        = int(request.POST.get('year', ''))
            start_month = int(request.POST.get('start_month', 1))
        except (ValueError, TypeError):
            year        = datetime.date.today().year
            start_month = 1
        try:
            from .scheduler import generate_schedule_with_ai
            generate_schedule_with_ai(year, start_month=start_month)
            messages.success(request, f'Cuadrante Producción generado desde {start_month}/{year}.')
        except Exception as e:
            messages.error(request, f'Error al generar: {str(e)}')
        return redirect(f'/schedule/?start_year={year}&start_month={start_month}')
    return redirect('calendar_view')


def generate_acondicionamiento_view(request):
    if request.method == 'POST':
        try:
            year        = int(request.POST.get('year', ''))
            start_month = int(request.POST.get('start_month', 1))
        except (ValueError, TypeError):
            year        = datetime.date.today().year
            start_month = 1
        try:
            from .scheduler import generate_schedule_acondicionamiento
            generate_schedule_acondicionamiento(year, start_month=start_month)
            messages.success(request, f'Cuadrante Acondicionamiento generado desde {start_month}/{year}.')
        except Exception as e:
            messages.error(request, f'Error al generar: {str(e)}')
        return redirect(f'/schedule/acondicionamiento/?start_year={year}&start_month={start_month}')
    return redirect('calendar_acondicionamiento')


def edit_assignment(request, pk):
    assignment = get_object_or_404(ShiftAssignment, pk=pk)
    if request.method == 'POST':
        new_shift = request.POST.get('shift')
        if new_shift in ['TM', 'TT', 'TN']:
            assignment.shift     = new_shift
            assignment.is_manual = True
            assignment.save()
            messages.success(request, 'Turno actualizado.')
    return redirect('calendar_view')