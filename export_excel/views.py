from django.http import HttpResponse
from .excel_builder import build_excel
import datetime


def export_excel(request):
    year = int(request.GET.get('year', datetime.date.today().year))

    wb       = build_excel(year)
    filename = f'cuadrante_{year}.xlsx'

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)

    return response
