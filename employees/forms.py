from django import forms
from .models import Employee


class EmployeeForm(forms.ModelForm):
    class Meta:
        model  = Employee
        fields = ['name', 'departamento', 'puede_TM', 'puede_TT', 'puede_TN', 'is_active']
        labels = {
            'name':         'Nombre y apellido',
            'departamento': 'Departamento',
            'puede_TM':     'Puede hacer TM (Mañana)',
            'puede_TT':     'Puede hacer TT (Tarde)',
            'puede_TN':     'Puede hacer TN (Noche)',
            'is_active':    'Empleado activo',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class':       'form-control',
                'placeholder': 'Ej: David Domingo',
            }),
            'departamento': forms.Select(attrs={
                'class': 'form-select',
            }),
            'puede_TM':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'puede_TT':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'puede_TN':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }