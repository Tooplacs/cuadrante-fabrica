from django import forms
from .models import Employee


class EmployeeForm(forms.ModelForm):
    class Meta:
        model  = Employee
        fields = ['name', 'departamento', 'puede_TM', 'puede_TT', 'puede_TN', 'en_baja', 'baja_inicio', 'baja_fin']
        labels = {
            'name':         'Nombre y apellido',
            'departamento': 'Departamento',
            'puede_TM':     'TM',
            'puede_TT':     'TT',
            'puede_TN':     'TN',
            'en_baja':      'En baja',
            'baja_inicio':  'Inicio baja',
            'baja_fin':     'Fin baja',
        }
        widgets = {
            'name':         forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: David Domingo'}),
            'departamento': forms.Select(attrs={'class': 'form-select'}),
            'puede_TM':     forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'puede_TT':     forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'puede_TN':     forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'en_baja':      forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'baja_inicio':  forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'baja_fin':     forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }