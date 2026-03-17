from django.db import models


class Employee(models.Model):

    name      = models.CharField(max_length=100)
    puede_TM  = models.BooleanField(default=True, verbose_name='TM')
    puede_TT  = models.BooleanField(default=True, verbose_name='TT')
    puede_TN  = models.BooleanField(default=True, verbose_name='TN')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

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