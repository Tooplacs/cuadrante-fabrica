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
    form = EmployeeForm(request.POST or None, instance=employee)
    if form.is_valid():
        form.save()
        return redirect('employee_list')
    return render(request, 'employees/employee_form.html', {
        'form':  form,
        'title': f'Modifier - {employee.name}',
    })


def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        employee.delete()
        return redirect('employee_list')
    return render(request, 'employees/employee_confirm_delete.html', {
        'employee': employee,
    })

