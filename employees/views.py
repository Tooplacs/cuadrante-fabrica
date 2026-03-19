from django.shortcuts import render, redirect, get_object_or_404
from .models import Employee
from .forms import EmployeeForm


def employee_list(request):
    produccion       = Employee.objects.filter(departamento='produccion')
    acondicionamiento = Employee.objects.filter(departamento='acondicionamiento')
    return render(request, 'employees/employee_list.html', {
        'produccion':        produccion,
        'acondicionamiento': acondicionamiento,
    })


def employee_create(request):
    form = EmployeeForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('employee_list')
    return render(request, 'employees/employee_form.html', {
        'form':  form,
        'title': 'Añadir un empleado',
    })


def employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    old_en_baja    = employee.en_baja
    old_baja_inicio = employee.baja_inicio
    form = EmployeeForm(request.POST or None, instance=employee)
    if form.is_valid():
        form.save()
        employee.refresh_from_db()
        # Si en_baja a changé ou dates modifiées → régénérer depuis baja_inicio
        if employee.en_baja and employee.baja_inicio:
            from schedule.scheduler import generate_schedule_with_ai, generate_schedule_acondicionamiento
            import datetime
            year        = employee.baja_inicio.year
            start_month = employee.baja_inicio.month
            if employee.departamento == 'produccion':
                generate_schedule_with_ai(year, start_month=start_month)
            else:
                generate_schedule_acondicionamiento(year, start_month=start_month)
        return redirect('employee_list')
    return render(request, 'employees/employee_form.html', {
        'form':  form,
        'title': f'Modificar - {employee.name}',
    })


def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        employee.delete()
        return redirect('employee_list')
    return render(request, 'employees/employee_confirm_delete.html', {
        'employee': employee,
    })

