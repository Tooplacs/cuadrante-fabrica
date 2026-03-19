from .models import ShiftAssignment
from employees.models import Employee
import random
from datetime import date

ALL_SHIFTS = ['TM', 'TT', 'TN']


def get_previous_shift(employee, year, month):
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    try:
        return ShiftAssignment.objects.get(
            employee=employee, year=prev_year, month=prev_month
        ).shift
    except ShiftAssignment.DoesNotExist:
        return None


def get_tn_count(employee):
    return ShiftAssignment.objects.filter(employee=employee, shift='TN').count()


def get_opposite(shift):
    if shift == 'TM':
        return 'TT'
    if shift == 'TT':
        return 'TM'
    return None


def is_employee_en_baja_for_month(emp, year, month):
    if not emp.en_baja:
        return False
    if not emp.baja_inicio or not emp.baja_fin:
        return True
    mois_date  = date(year, month, 1)
    baja_debut = emp.baja_inicio.replace(day=1)
    baja_fin   = emp.baja_fin.replace(day=1)
    return baja_debut <= mois_date <= baja_fin


def get_last_real_shift(emp, year, month):
    """Retourne le dernier shift réel (non BJ) avant ce mois."""
    y, m = year, month
    for _ in range(24):
        if m == 1:
            y, m = y - 1, 12
        else:
            m -= 1
        try:
            a = ShiftAssignment.objects.get(employee=emp, year=y, month=m)
            if a.shift not in ('BJ', None):
                return a.shift
        except ShiftAssignment.DoesNotExist:
            pass
    return None


def generate_schedule_with_ai(year, start_month=1):
    all_employees    = list(Employee.objects.filter(departamento='produccion'))
    active_employees = all_employees[:]

    if not all_employees:
        return {}

    ShiftAssignment.objects.filter(
        year=year,
        month__gte=start_month,
        employee__departamento='produccion',
        is_manual=False,
    ).delete()

    manuels = {
        (a.employee_id, a.month): a.shift
        for a in ShiftAssignment.objects.filter(
            year=year,
            employee__departamento='produccion',
            is_manual=True,
        )
    }

    fixed_emps = [e for e in active_employees if len(e.allowed_shifts()) == 1]
    free_emps  = [e for e in active_employees if len(e.allowed_shifts()) > 1]

    tn_eligible = [e for e in free_emps if 'TN' in e.allowed_shifts()]
    if not tn_eligible:
        tn_eligible = free_emps[:] if free_emps else []

    tn_counts = {emp.id: 0 for emp in tn_eligible}

    # Initialiser prev_shifts avec le dernier shift réel (non BJ)
    prev_shifts = {}
    for emp in active_employees:
        prev_shifts[emp.id] = get_last_real_shift(emp, year, start_month)

    free_order = free_emps[:]
    random.shuffle(free_order)

    for month in range(start_month, 13):
        assignments = {}

        active_this_month = [
            e for e in active_employees
            if not is_employee_en_baja_for_month(e, year, month)
        ]
        fixed_this_month = [e for e in fixed_emps if e in active_this_month]
        free_this_month  = [e for e in free_order  if e in active_this_month]

        # 1. Fixes
        for emp in fixed_this_month:
            assignments[emp.id] = emp.allowed_shifts()[0]

        # 2. TN — 1 par mois obligatoire, jamais 2 mois de suite
        tn_eligible_this_month = [e for e in tn_eligible if e in active_this_month]
        if tn_eligible_this_month:
            tn_sorted = sorted(tn_eligible_this_month, key=lambda e: tn_counts[e.id])
            tn_emp    = None
            for candidate in tn_sorted:
                if prev_shifts.get(candidate.id) != 'TN':
                    tn_emp = candidate
                    break
            if tn_emp is None:
                tn_emp = tn_sorted[0]
            assignments[tn_emp.id] = 'TN'
            tn_counts[tn_emp.id] += 1

        # 3. Quotas TM/TT — alternance sur le TOTAL actif ce mois
        remaining        = [e for e in free_this_month if e.id not in assignments]
        n_remaining      = len(remaining)
        n_fixed_tm       = sum(1 for emp in fixed_this_month if assignments.get(emp.id) == 'TM')
        n_fixed_tt       = sum(1 for emp in fixed_this_month if assignments.get(emp.id) == 'TT')
        total_emps_no_tn = len(fixed_this_month) + n_remaining

        if month % 2 == 1:
            target_tm = (total_emps_no_tn + 1) // 2
            target_tt = total_emps_no_tn // 2
        else:
            target_tm = total_emps_no_tn // 2
            target_tt = (total_emps_no_tn + 1) // 2

        n_tm_need = max(0, target_tm - n_fixed_tm)
        n_tt_need = max(0, target_tt - n_fixed_tt)

        # 4. TM/TT — alternance individuelle PRIORITAIRE sur les quotas
        must_change = []
        can_choose  = []

        for emp in remaining:
            allowed = emp.allowed_shifts()
            non_tn  = [s for s in allowed if s != 'TN']
            prev    = prev_shifts.get(emp.id)
            opp     = get_opposite(prev) if prev in ['TM', 'TT'] else None
            if opp and opp in non_tn:
                must_change.append((emp, opp))
            else:
                can_choose.append(emp)

        random.shuffle(must_change)
        random.shuffle(can_choose)
        tm_count = tt_count = 0

        # must_change : forcer l'alternance sans condition de quota
        for emp, forced_shift in must_change:
            assignments[emp.id] = forced_shift
            if forced_shift == 'TM':
                tm_count += 1
            elif forced_shift == 'TT':
                tt_count += 1

        # can_choose : remplir avec les quotas restants
        for emp in can_choose:
            allowed = emp.allowed_shifts()
            non_tn  = [s for s in allowed if s != 'TN']
            if tm_count < n_tm_need and 'TM' in non_tn:
                assignments[emp.id] = 'TM'; tm_count += 1
            elif tt_count < n_tt_need and 'TT' in non_tn:
                assignments[emp.id] = 'TT'; tt_count += 1
            elif 'TM' in non_tn:
                assignments[emp.id] = 'TM'; tm_count += 1
            elif 'TT' in non_tn:
                assignments[emp.id] = 'TT'; tt_count += 1
            else:
                assignments[emp.id] = non_tn[0] if non_tn else allowed[0]

        # Sauvegarder
        for emp in all_employees:
            manuel = manuels.get((emp.id, month))
            if manuel:
                assignments[emp.id] = manuel
                ShiftAssignment.objects.update_or_create(
                    employee=emp, year=year, month=month,
                    defaults={'shift': manuel, 'is_manual': True},
                )
            elif emp.id in assignments:
                ShiftAssignment.objects.update_or_create(
                    employee=emp, year=year, month=month,
                    defaults={'shift': assignments[emp.id], 'is_manual': False},
                )
            else:
                ShiftAssignment.objects.update_or_create(
                    employee=emp, year=year, month=month,
                    defaults={'shift': 'BJ', 'is_manual': False},
                )
                assignments[emp.id] = 'BJ'

        # prev_shifts — garder le dernier shift réel connu (non BJ)
        new_prev = {}
        for emp in active_employees:
            shift = assignments.get(emp.id)
            if shift and shift != 'BJ':
                new_prev[emp.id] = shift
            else:
                new_prev[emp.id] = prev_shifts.get(emp.id)
        prev_shifts = new_prev

    return {}


def generate_schedule_acondicionamiento(year, start_month=1):
    all_employees    = list(Employee.objects.filter(departamento='acondicionamiento'))
    active_employees = all_employees[:]

    if not all_employees:
        return {}

    ShiftAssignment.objects.filter(
        year=year,
        month__gte=start_month,
        employee__departamento='acondicionamiento',
        is_manual=False,
    ).delete()

    manuels = {
        (a.employee_id, a.month): a.shift
        for a in ShiftAssignment.objects.filter(
            year=year,
            employee__departamento='acondicionamiento',
            is_manual=True,
        )
    }

    fixed_emps = [e for e in active_employees if len(e.allowed_shifts()) == 1]
    free_emps  = [e for e in active_employees if len(e.allowed_shifts()) > 1]

    tn_eligible = [e for e in free_emps if 'TN' in e.allowed_shifts()]
    if not tn_eligible:
        tn_eligible = free_emps[:] if free_emps else []

    tn_counts = {emp.id: 0 for emp in tn_eligible}

    # Initialiser prev_shifts avec le dernier shift réel (non BJ)
    prev_shifts = {}
    for emp in active_employees:
        prev_shifts[emp.id] = get_last_real_shift(emp, year, start_month)

    free_order = free_emps[:]
    random.shuffle(free_order)

    for month in range(start_month, 13):
        assignments = {}

        active_this_month = [
            e for e in active_employees
            if not is_employee_en_baja_for_month(e, year, month)
        ]
        fixed_this_month = [e for e in fixed_emps if e in active_this_month]
        free_this_month  = [e for e in free_order  if e in active_this_month]

        for emp in fixed_this_month:
            assignments[emp.id] = emp.allowed_shifts()[0]

        tn_eligible_this_month = [e for e in tn_eligible if e in active_this_month]
        if tn_eligible_this_month:
            tn_sorted = sorted(tn_eligible_this_month, key=lambda e: tn_counts[e.id])
            tn_emp    = None
            for candidate in tn_sorted:
                if prev_shifts.get(candidate.id) != 'TN':
                    tn_emp = candidate
                    break
            if tn_emp is None:
                tn_emp = tn_sorted[0]
            assignments[tn_emp.id] = 'TN'
            tn_counts[tn_emp.id] += 1

        remaining        = [e for e in free_this_month if e.id not in assignments]
        n_remaining      = len(remaining)
        n_fixed_tm       = sum(1 for emp in fixed_this_month if assignments.get(emp.id) == 'TM')
        n_fixed_tt       = sum(1 for emp in fixed_this_month if assignments.get(emp.id) == 'TT')
        total_emps_no_tn = len(fixed_this_month) + n_remaining

        if month % 2 == 1:
            target_tm = (total_emps_no_tn + 1) // 2
            target_tt = total_emps_no_tn // 2
        else:
            target_tm = total_emps_no_tn // 2
            target_tt = (total_emps_no_tn + 1) // 2

        n_tm_need = max(0, target_tm - n_fixed_tm)
        n_tt_need = max(0, target_tt - n_fixed_tt)

        must_change = []
        can_choose  = []

        for emp in remaining:
            allowed = emp.allowed_shifts()
            non_tn  = [s for s in allowed if s != 'TN']
            prev    = prev_shifts.get(emp.id)
            opp     = get_opposite(prev) if prev in ['TM', 'TT'] else None
            if opp and opp in non_tn:
                must_change.append((emp, opp))
            else:
                can_choose.append(emp)

        random.shuffle(must_change)
        random.shuffle(can_choose)
        tm_count = tt_count = 0

        # must_change : forcer l'alternance sans condition de quota
        for emp, forced_shift in must_change:
            assignments[emp.id] = forced_shift
            if forced_shift == 'TM':
                tm_count += 1
            elif forced_shift == 'TT':
                tt_count += 1

        # can_choose : remplir avec les quotas restants
        for emp in can_choose:
            allowed = emp.allowed_shifts()
            non_tn  = [s for s in allowed if s != 'TN']
            if tm_count < n_tm_need and 'TM' in non_tn:
                assignments[emp.id] = 'TM'; tm_count += 1
            elif tt_count < n_tt_need and 'TT' in non_tn:
                assignments[emp.id] = 'TT'; tt_count += 1
            elif 'TM' in non_tn:
                assignments[emp.id] = 'TM'; tm_count += 1
            elif 'TT' in non_tn:
                assignments[emp.id] = 'TT'; tt_count += 1
            else:
                assignments[emp.id] = non_tn[0] if non_tn else allowed[0]

        for emp in all_employees:
            manuel = manuels.get((emp.id, month))
            if manuel:
                assignments[emp.id] = manuel
                ShiftAssignment.objects.update_or_create(
                    employee=emp, year=year, month=month,
                    defaults={'shift': manuel, 'is_manual': True},
                )
            elif emp.id in assignments:
                ShiftAssignment.objects.update_or_create(
                    employee=emp, year=year, month=month,
                    defaults={'shift': assignments[emp.id], 'is_manual': False},
                )
            else:
                ShiftAssignment.objects.update_or_create(
                    employee=emp, year=year, month=month,
                    defaults={'shift': 'BJ', 'is_manual': False},
                )
                assignments[emp.id] = 'BJ'

        # prev_shifts — garder le dernier shift réel connu (non BJ)
        new_prev = {}
        for emp in active_employees:
            shift = assignments.get(emp.id)
            if shift and shift != 'BJ':
                new_prev[emp.id] = shift
            else:
                new_prev[emp.id] = prev_shifts.get(emp.id)
        prev_shifts = new_prev

    return {}


def generate_schedule(year, month, overwrite=False):
    employees = list(Employee.objects.filter(en_baja=False))

    for emp in employees:
        existing = ShiftAssignment.objects.filter(
            employee=emp, year=year, month=month
        ).first()
        if existing:
            if not overwrite and existing.is_manual:
                continue
            existing.delete()

    prev  = {e.id: get_previous_shift(e, year, month) for e in employees}
    fixed = [e for e in employees if len(e.allowed_shifts()) == 1]
    free  = [e for e in employees if len(e.allowed_shifts()) > 1]

    assignments = {}

    for emp in fixed:
        assignments[emp.id] = emp.allowed_shifts()[0]

    if free:
        tn_eligible = [
            e for e in free
            if prev[e.id] != 'TN' and 'TN' in e.allowed_shifts()
        ]
        tn_eligible.sort(key=lambda e: (get_tn_count(e), random.random()))
        tn_emp = tn_eligible[0] if tn_eligible else None
        if tn_emp:
            assignments[tn_emp.id] = 'TN'

        remaining = [e for e in free if e.id not in assignments]
        random.shuffle(remaining)

        n_lib     = len(remaining)
        n_tt_need = n_lib // 2
        n_tm_need = n_lib - n_tt_need
        tm_count  = 0
        tt_count  = 0

        constrained   = [e for e in remaining if prev[e.id] in ['TM', 'TT']]
        unconstrained = [e for e in remaining if prev[e.id] not in ['TM', 'TT']]

        for emp in constrained:
            allowed = emp.allowed_shifts()
            non_tn  = [s for s in allowed if s != 'TN']
            p       = prev[emp.id]
            if p == 'TM' and 'TT' in non_tn and tt_count < n_tt_need:
                assignments[emp.id] = 'TT'; tt_count += 1
            elif p == 'TT' and 'TM' in non_tn and tm_count < n_tm_need:
                assignments[emp.id] = 'TM'; tm_count += 1
            elif tm_count < n_tm_need and 'TM' in non_tn:
                assignments[emp.id] = 'TM'; tm_count += 1
            elif 'TT' in non_tn:
                assignments[emp.id] = 'TT'; tt_count += 1
            else:
                assignments[emp.id] = non_tn[0] if non_tn else allowed[0]

        for emp in unconstrained:
            allowed = emp.allowed_shifts()
            non_tn  = [s for s in allowed if s != 'TN']
            if tm_count < n_tm_need and 'TM' in non_tn:
                assignments[emp.id] = 'TM'; tm_count += 1
            elif 'TT' in non_tn:
                assignments[emp.id] = 'TT'; tt_count += 1
            else:
                assignments[emp.id] = non_tn[0] if non_tn else allowed[0]

    for emp in employees:
        if emp.id in assignments:
            ShiftAssignment.objects.create(
                employee=emp, year=year, month=month,
                shift=assignments[emp.id], is_manual=False,
            )


def get_schedule_for_period(start_year, start_month, num_months, departamento=None):
    import calendar

    data        = []
    year, month = start_year, start_month

    for _ in range(num_months):
        qs = ShiftAssignment.objects.filter(year=year, month=month)
        if departamento:
            qs = qs.filter(employee__departamento=departamento)

        if not qs.exists():
            generate_schedule(year, month)

        assignments = ShiftAssignment.objects.filter(
            year=year, month=month
        ).select_related('employee')

        if departamento:
            assignments = assignments.filter(employee__departamento=departamento)

        # Annoter chaque assignment avec is_baja_mois
        mois_date = date(year, month, 1)
        for a in assignments:
            emp = a.employee
            if a.shift == 'BJ':
                a.is_baja_mois = True
            elif emp.en_baja and emp.baja_inicio and emp.baja_fin:
                baja_debut    = emp.baja_inicio.replace(day=1)
                baja_fin_date = emp.baja_fin.replace(day=1)
                a.is_baja_mois = (baja_debut <= mois_date <= baja_fin_date)
            else:
                a.is_baja_mois = False

        counts = {'TM': 0, 'TT': 0, 'TN': 0}
        for a in assignments:
            if not a.is_baja_mois and a.shift in counts:
                counts[a.shift] += 1

        abbr  = calendar.month_abbr[month]
        label = f"{abbr}-{str(year)[2:]}"

        data.append({
            'year':        year,
            'month':       month,
            'label':       label,
            'assignments': assignments,
            'counts':      counts,
        })

        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1

    return data