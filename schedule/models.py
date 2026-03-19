from django.db import models
from employees.models import Employee


class ShiftAssignment(models.Model):

    SHIFT_CHOICES = [
        ('TM', 'Matin'),
        ('TT', 'Après-midi'),
        ('TN', 'Nuit'),
        ('BJ', 'Baja'),
    ]

    employee  = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='assignments')
    year      = models.IntegerField()
    month     = models.IntegerField()
    shift     = models.CharField(max_length=2, choices=SHIFT_CHOICES)
    is_manual = models.BooleanField(default=False)

    class Meta:
        unique_together = ('employee', 'year', 'month')
        ordering = ['year', 'month', 'employee']

    def __str__(self):
        return f"{self.employee.name} — {self.month}/{self.year} : {self.shift}"

    @property
    def month_label(self):
        import calendar
        abbr = calendar.month_abbr[self.month]
        return f"{abbr}-{str(self.year)[2:]}"