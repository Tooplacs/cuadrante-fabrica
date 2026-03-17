from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import ShiftAssignment
from .scheduler import generate_schedule, get_schedule_for_period
from employees.models import Employee
import datetime


def calendar_view(request):
    today      = datetime.date.today()
    start_year = int(request.GET.get('start_year', today.year))

    employees = Employee.objects.filter(is_active=True)
    period    = get_schedule_for_period(start_year, 1, 12)

    return render(request, 'schedule/calendar_view.html', {
        'employees':   employees,
        'period':      period,
        'start_year':  start_year,
    })


def generate_view(request):
    if request.method == 'POST':
        try:
            year = int(request.POST.get('year', ''))
        except (ValueError, TypeError):
            year = datetime.date.today().year

        try:
            from .scheduler import generate_schedule_with_ai
            generate_schedule_with_ai(year)
            messages.success(request, f'Cuadrante generado con IA para el año {year}.')
        except Exception as e:
            messages.error(request, f'Error al generar: {str(e)}')
        return redirect(f'/schedule/?start_year={year}')
    return redirect('calendar_view')


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