from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import calendar

from schedule.models import ShiftAssignment
from employees.models import Employee

COLOR_HEADER_BG = '009B9B'
COLOR_NAME_BG   = '009B9B'
COLOR_TM_BG     = 'C6EFCE'
COLOR_TT_BG     = 'FFEB9C'
COLOR_TN_BG     = '0070C0'
COLOR_TEXT_TM   = '006100'
COLOR_TEXT_TT   = '9C5700'
COLOR_TEXT_TN   = '9C0006'
COLOR_WHITE     = 'FFFFFF'
COLOR_BLACK     = '000000'


def get_border():
    thin = Side(style='thin', color='AAAAAA')
    return Border(left=thin, right=thin, top=thin, bottom=thin)


def apply_cell(ws, row, col, value, bg_color, font_color=COLOR_BLACK,
               bold=False, italic=False, align='center'):
    cell           = ws.cell(row=row, column=col, value=value)
    cell.fill      = PatternFill('solid', start_color=bg_color)
    cell.font      = Font(name='Calibri', bold=bold, italic=italic,
                          color=font_color, size=11)
    cell.alignment = Alignment(horizontal=align, vertical='center')
    cell.border    = get_border()
    return cell


def build_excel(year, start_month=1, num_months=12):
    employees = list(Employee.objects.filter(is_active=True).order_by('name'))
    wb        = Workbook()
    ws        = wb.active
    ws.title  = f'Cuadrante {year}'

    for i in range(1, len(employees) + 6):
        ws.row_dimensions[i].height = 20

    ws.column_dimensions['A'].width = 22

    months = []
    m_year, m_month = year, start_month
    for _ in range(num_months):
        abbr  = calendar.month_abbr[m_month]
        label = f"{abbr}-{str(m_year)[2:]}"
        months.append((m_year, m_month, label))
        if m_month == 12:
            m_year, m_month = m_year + 1, 1
        else:
            m_month += 1

    for i in range(num_months):
        ws.column_dimensions[get_column_letter(i + 2)].width = 8

    # Ligne 1 : entetes mois
    apply_cell(ws, 1, 1, '', COLOR_HEADER_BG, COLOR_WHITE, bold=True)
    for col_idx, (m_year, m_month, label) in enumerate(months, start=2):
        apply_cell(ws, 1, col_idx, label, COLOR_HEADER_BG,
                   COLOR_WHITE, bold=True)

    # Lignes employes
    for row_idx, emp in enumerate(employees, start=2):
        apply_cell(ws, row_idx, 1, emp.name, COLOR_NAME_BG,
                   COLOR_WHITE, bold=True, italic=True, align='left')

        for col_idx, (m_year, m_month, label) in enumerate(months, start=2):
            try:
                assignment = ShiftAssignment.objects.get(
                    employee=emp, year=m_year, month=m_month
                )
                shift = assignment.shift
            except ShiftAssignment.DoesNotExist:
                shift = ''

            if shift == 'TM':
                bg   = COLOR_TM_BG
                fg   = COLOR_TEXT_TM
            elif shift == 'TT':
                bg   = COLOR_TT_BG
                fg   = COLOR_TEXT_TT
            elif shift == 'TN':
                bg   = COLOR_TN_BG
                fg   = COLOR_TEXT_TN
            else:
                bg   = COLOR_WHITE
                fg   = COLOR_BLACK

            apply_cell(ws, row_idx, col_idx, shift, bg, fg, bold=True)

    # Lignes compteurs
    count_row_tm = len(employees) + 2
    count_row_tt = len(employees) + 3
    count_row_tn = len(employees) + 4

    # Colonne gauche coloree
    apply_cell(ws, count_row_tm, 1, 'TM', COLOR_TM_BG,
               COLOR_TEXT_TM, bold=True, italic=True)
    apply_cell(ws, count_row_tt, 1, 'TT', COLOR_TT_BG,
               COLOR_TEXT_TT, bold=True, italic=True)
    apply_cell(ws, count_row_tn, 1, 'TN', COLOR_TN_BG,
               COLOR_TEXT_TN, bold=True, italic=True)

    # Lignes compteurs avec formules Excel
    for col_idx, (m_year, m_month, label) in enumerate(months, start=2):
        col_letter = get_column_letter(col_idx)
        first_emp_row = 2
        last_emp_row  = len(employees) + 1

        # Formule COUNTIF pour compter TM, TT, TN dans la colonne
        formula_tm = f'=COUNTIF({col_letter}{first_emp_row}:{col_letter}{last_emp_row},"TM")'
        formula_tt = f'=COUNTIF({col_letter}{first_emp_row}:{col_letter}{last_emp_row},"TT")'
        formula_tn = f'=COUNTIF({col_letter}{first_emp_row}:{col_letter}{last_emp_row},"TN")'

        apply_cell(ws, count_row_tm, col_idx,
                   formula_tm, COLOR_WHITE, COLOR_BLACK, bold=True)
        apply_cell(ws, count_row_tt, col_idx,
                   formula_tt, COLOR_WHITE, COLOR_BLACK, bold=True)
        apply_cell(ws, count_row_tn, col_idx,
                   formula_tn, COLOR_WHITE, COLOR_BLACK, bold=True)

    return wb