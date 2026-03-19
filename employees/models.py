from django.db import models


class Employee(models.Model):

    DEPARTAMENTO_CHOICES = [
        ('produccion',        'Producción'),
        ('acondicionamiento', 'Acondicionamiento'),
    ]

    name           = models.CharField(max_length=100)
    departamento   = models.CharField(max_length=20, choices=DEPARTAMENTO_CHOICES, default='produccion')
    puede_TM       = models.BooleanField(default=True, verbose_name='TM')
    puede_TT       = models.BooleanField(default=True, verbose_name='TT')
    puede_TN       = models.BooleanField(default=True, verbose_name='TN')
    en_baja        = models.BooleanField(default=False, verbose_name='En baja')
    baja_inicio    = models.DateField(null=True, blank=True, verbose_name='Inicio baja')
    baja_fin       = models.DateField(null=True, blank=True, verbose_name='Fin baja')

    class Meta:
        ordering = ['departamento', 'name']

    def __str__(self):
        return self.name

    def allowed_shifts(self):
        shifts = []
        if self.puede_TM:
            shifts.append('TM')
        if self.puede_TT:
            shifts.append('TT')
        if self.puede_TN:
            shifts.append('TN')
        return shifts if shifts else ['TM']