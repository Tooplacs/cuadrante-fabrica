from .models import ShiftAssignment
from employees.models import Employee
import random

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


def calculate_targets(fixed_emps, free_emps):
    fixed_tm = len([e for e in fixed_emps if e.allowed_shifts()[0] == 'TM'])
    fixed_tt = len([e for e in fixed_emps if e.allowed_shifts()[0] == 'TT'])

    n_libre_sans_tn = len(free_emps) - 1

    # Chercher la paire (n_tm_a, n_tm_b) qui :
    # 1. Equilibre la moyenne TM/TT sur les deux mois
    # 2. Difference de max 1 entre les deux mois
    # 3. Difference de max 1 entre TM et TT chaque mois

    best_pair  = None
    best_score = 999

    for n_tm_a in range(0, n_libre_sans_tn + 1):
        n_tt_a = n_libre_sans_tn - n_tm_a

        for n_tm_b in range(0, n_libre_sans_tn + 1):
            n_tt_b = n_libre_sans_tn - n_tm_b

            total_a_tm = n_tm_a + fixed_tm
            total_a_tt = n_tt_a + fixed_tt
            total_b_tm = n_tm_b + fixed_tm
            total_b_tt = n_tt_b + fixed_tt

            # Condition : difference max 1 entre TM et TT chaque mois
            if abs(total_a_tm - total_a_tt) > 1:
                continue
            if abs(total_b_tm - total_b_tt) > 1:
                continue

            # Score : ecart sur la moyenne + penalite si pas d'alternance
            avg_tm = (total_a_tm + total_b_tm) / 2
            avg_tt = (total_a_tt + total_b_tt) / 2
            score  = abs(avg_tm - avg_tt)

            if n_tm_a == n_tm_b:
                score += 0.5  # penalite si pas d'alternance

            if score < best_score:
                best_score = score
                best_pair  = (n_tm_a, n_tt_a, n_tm_b, n_tt_b)

    if best_pair:
        return best_pair

    # Fallback : distribution simple
    n_tm = n_libre_sans_tn // 2
    n_tt = n_libre_sans_tn - n_tm
    return n_tm, n_tt, n_tm, n_tt


def generate_schedule_with_ai(year):
    employees = list(Employee.objects.filter(is_active=True))
    if not employees:
        return {}

    ShiftAssignment.objects.filter(year=year).delete()

    fixed_emps = [e for e in employees if len(e.allowed_shifts()) == 1]
    free_emps  = [e for e in employees if len(e.allowed_shifts()) > 1]

    if not free_emps:
        for month in range(1, 13):
            for emp in fixed_emps:
                ShiftAssignment.objects.create(
                    employee=emp, year=year, month=month,
                    shift=emp.allowed_shifts()[0], is_manual=False,
                )
        return {}

    n_tm_odd, n_tt_odd, n_tm_even, n_tt_even = calculate_targets(fixed_emps, free_emps)

    tn_eligible = [e for e in free_emps if 'TN' in e.allowed_shifts()]
    if not tn_eligible:
        tn_eligible = free_emps[:]

    random.shuffle(tn_eligible)
    tn_eligible.sort(key=lambda e: (get_tn_count(e), random.random()))
    tn_index = 0

    prev_shifts = {emp.id: get_previous_shift(emp, year, 1) for emp in employees}
    free_order  = free_emps[:]
    random.shuffle(free_order)

    for month in range(1, 13):
        assignments = {}

        n_tm_need = n_tm_odd  if month % 2 == 1 else n_tm_even
        n_tt_need = n_tt_odd  if month % 2 == 1 else n_tt_even

        # 1. Fixes
        for emp in fixed_emps:
            assignments[emp.id] = emp.allowed_shifts()[0]

        # 2. TN par rotation
        tn_emp   = None
        attempts = 0
        while attempts < len(tn_eligible):
            candidate = tn_eligible[(tn_index + attempts) % len(tn_eligible)]
            if prev_shifts.get(candidate.id) != 'TN':
                tn_emp   = candidate
                tn_index = (tn_index + attempts + 1) % len(tn_eligible)
                break
            attempts += 1

        if tn_emp:
            assignments[tn_emp.id] = 'TN'

        # 3. TM/TT avec alternance forcee individuelle
        remaining = [e for e in free_order if e.id not in assignments]
        tm_count  = 0
        tt_count  = 0

        # Trier : ceux qui ont DEJA fait le meme quart 2+ mois en priorite de changement
        def change_priority(emp):
            prev = prev_shifts.get(emp.id)
            if prev in ['TM', 'TT']:
                return 0  # priorite haute : doit changer
            return 1

        remaining_sorted = sorted(remaining, key=change_priority)
        random.shuffle(remaining_sorted)
        remaining_sorted.sort(key=change_priority)

        for emp in remaining_sorted:
            allowed = emp.allowed_shifts()
            non_tn  = [s for s in allowed if s != 'TN']
            prev    = prev_shifts.get(emp.id)
            opp     = get_opposite(prev) if prev in ['TM', 'TT'] else None

            if opp and opp in non_tn:
                # Doit changer — assigner l'oppose si quota disponible
                if opp == 'TM' and tm_count < n_tm_need:
                    assignments[emp.id] = 'TM'; tm_count += 1
                elif opp == 'TT' and tt_count < n_tt_need:
                    assignments[emp.id] = 'TT'; tt_count += 1
                elif opp == 'TM' and tt_count < n_tt_need and 'TT' in non_tn:
                    assignments[emp.id] = 'TT'; tt_count += 1
                elif opp == 'TT' and tm_count < n_tm_need and 'TM' in non_tn:
                    assignments[emp.id] = 'TM'; tm_count += 1
                else:
                    assignments[emp.id] = opp
            else:
                if tm_count < n_tm_need and 'TM' in non_tn:
                    assignments[emp.id] = 'TM'; tm_count += 1
                elif tt_count < n_tt_need and 'TT' in non_tn:
                    assignments[emp.id] = 'TT'; tt_count += 1
                else:
                    assignments[emp.id] = non_tn[0] if non_tn else allowed[0]

        # Sauvegarder
        for emp in employees:
            if emp.id in assignments:
                ShiftAssignment.objects.create(
                    employee=emp,
                    year=year,
                    month=month,
                    shift=assignments[emp.id],
                    is_manual=False,
                )

        prev_shifts = {emp.id: assignments.get(emp.id) for emp in employees}

    return {}


def generate_schedule_with_ai(year):
    employees = list(Employee.objects.filter(is_active=True))
    if not employees:
        return {}

    ShiftAssignment.objects.filter(year=year).delete()

    fixed_emps = [e for e in employees if len(e.allowed_shifts()) == 1]
    free_emps  = [e for e in employees if len(e.allowed_shifts()) > 1]

    if not free_emps:
        for month in range(1, 13):
            for emp in fixed_emps:
                ShiftAssignment.objects.create(
                    employee=emp, year=year, month=month,
                    shift=emp.allowed_shifts()[0], is_manual=False,
                )
        return {}

    n_tm_odd, n_tt_odd, n_tm_even, n_tt_even = calculate_targets(fixed_emps, free_emps)

    tn_eligible = [e for e in free_emps if 'TN' in e.allowed_shifts()]
    if not tn_eligible:
        tn_eligible = free_emps[:]

    random.shuffle(tn_eligible)
    tn_eligible.sort(key=lambda e: (get_tn_count(e), random.random()))
    tn_index = 0

    prev_shifts = {emp.id: get_previous_shift(emp, year, 1) for emp in employees}

    # Ordre aleatoire des libres, stable sur l'annee
    free_order = free_emps[:]
    random.shuffle(free_order)

    for month in range(1, 13):
        assignments = {}

        n_tm_need = n_tm_odd  if month % 2 == 1 else n_tm_even
        n_tt_need = n_tt_odd  if month % 2 == 1 else n_tt_even

        # 1. Fixes
        for emp in fixed_emps:
            assignments[emp.id] = emp.allowed_shifts()[0]

        # 2. TN par rotation
        tn_emp   = None
        attempts = 0
        while attempts < len(tn_eligible):
            candidate = tn_eligible[(tn_index + attempts) % len(tn_eligible)]
            if prev_shifts.get(candidate.id) != 'TN':
                tn_emp   = candidate
                tn_index = (tn_index + attempts + 1) % len(tn_eligible)
                break
            attempts += 1

        if tn_emp:
            assignments[tn_emp.id] = 'TN'

        # 3. TM/TT — forcer l'alternance individuelle
        remaining = [e for e in free_order if e.id not in assignments]

        tm_count = 0
        tt_count = 0

        # Passe 1 : employes qui DOIVENT changer (prev TM -> TT, prev TT -> TM)
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

        for emp, forced_shift in must_change:
            if forced_shift == 'TM' and tm_count < n_tm_need:
                assignments[emp.id] = 'TM'; tm_count += 1
            elif forced_shift == 'TT' and tt_count < n_tt_need:
                assignments[emp.id] = 'TT'; tt_count += 1
            elif forced_shift == 'TM' and 'TT' in emp.allowed_shifts():
                assignments[emp.id] = 'TT'; tt_count += 1
            elif forced_shift == 'TT' and 'TM' in emp.allowed_shifts():
                assignments[emp.id] = 'TM'; tm_count += 1
            else:
                assignments[emp.id] = forced_shift

        for emp in can_choose:
            allowed = emp.allowed_shifts()
            non_tn  = [s for s in allowed if s != 'TN']

            if tm_count < n_tm_need and 'TM' in non_tn:
                assignments[emp.id] = 'TM'; tm_count += 1
            elif tt_count < n_tt_need and 'TT' in non_tn:
                assignments[emp.id] = 'TT'; tt_count += 1
            elif tm_count < n_tm_need and 'TM' in non_tn:
                assignments[emp.id] = 'TM'; tm_count += 1
            else:
                assignments[emp.id] = non_tn[0] if non_tn else allowed[0]

        # Sauvegarder
        for emp in employees:
            if emp.id in assignments:
                ShiftAssignment.objects.create(
                    employee=emp,
                    year=year,
                    month=month,
                    shift=assignments[emp.id],
                    is_manual=False,
                )

        prev_shifts = {emp.id: assignments.get(emp.id) for emp in employees}

    return {}


def generate_schedule(year, month, overwrite=False):
    employees = list(Employee.objects.filter(is_active=True))

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
                employee=emp,
                year=year,
                month=month,
                shift=assignments[emp.id],
                is_manual=False,
            )


def get_schedule_for_period(start_year, start_month, num_months, departamento=None):
    import calendar

    data        = []
    year, month = start_year, start_month

    for _ in range(num_months):
        assignments = ShiftAssignment.objects.filter(
            year=year, month=month
        ).select_related('employee')

        if departamento:
            assignments = assignments.filter(employee__departamento=departamento)

        if not assignments.exists():
            generate_schedule(year, month)
            assignments = ShiftAssignment.objects.filter(
                year=year, month=month
            ).select_related('employee')
            if departamento:
                assignments = assignments.filter(employee__departamento=departamento)

        counts = {'TM': 0, 'TT': 0, 'TN': 0}
        for a in assignments:
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

def generate_schedule_acondicionamiento(year):
    employees = list(Employee.objects.filter(is_active=True, departamento='acondicionamiento'))
    if not employees:
        return {}

    ShiftAssignment.objects.filter(year=year, employee__departamento='acondicionamiento').delete()

    fixed_emps = [e for e in employees if len(e.allowed_shifts()) == 1]
    free_emps  = [e for e in employees if len(e.allowed_shifts()) > 1]

    if not free_emps:
        for month in range(1, 13):
            for emp in fixed_emps:
                ShiftAssignment.objects.create(
                    employee=emp, year=year, month=month,
                    shift=emp.allowed_shifts()[0], is_manual=False,
                )
        return {}

    n_tm_odd, n_tt_odd, n_tm_even, n_tt_even = calculate_targets(fixed_emps, free_emps)

    tn_eligible = [e for e in free_emps if 'TN' in e.allowed_shifts()]
    if not tn_eligible:
        tn_eligible = free_emps[:]

    random.shuffle(tn_eligible)
    tn_eligible.sort(key=lambda e: (get_tn_count(e), random.random()))
    tn_index = 0

    prev_shifts = {emp.id: get_previous_shift(emp, year, 1) for emp in employees}
    free_order  = free_emps[:]
    random.shuffle(free_order)

    for month in range(1, 13):
        assignments  = {}
        n_tm_need    = n_tm_odd if month % 2 == 1 else n_tm_even
        n_tt_need    = n_tt_odd if month % 2 == 1 else n_tt_even

        for emp in fixed_emps:
            assignments[emp.id] = emp.allowed_shifts()[0]

        tn_emp   = None
        attempts = 0
        while attempts < len(tn_eligible):
            candidate = tn_eligible[(tn_index + attempts) % len(tn_eligible)]
            if prev_shifts.get(candidate.id) != 'TN':
                tn_emp   = candidate
                tn_index = (tn_index + attempts + 1) % len(tn_eligible)
                break
            attempts += 1

        if tn_emp:
            assignments[tn_emp.id] = 'TN'

        remaining   = [e for e in free_order if e.id not in assignments]
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

        for emp, forced_shift in must_change:
            if forced_shift == 'TM' and tm_count < n_tm_need:
                assignments[emp.id] = 'TM'; tm_count += 1
            elif forced_shift == 'TT' and tt_count < n_tt_need:
                assignments[emp.id] = 'TT'; tt_count += 1
            elif forced_shift == 'TM' and 'TT' in emp.allowed_shifts():
                assignments[emp.id] = 'TT'; tt_count += 1
            elif forced_shift == 'TT' and 'TM' in emp.allowed_shifts():
                assignments[emp.id] = 'TM'; tm_count += 1
            else:
                assignments[emp.id] = forced_shift

        for emp in can_choose:
            allowed = emp.allowed_shifts()
            non_tn  = [s for s in allowed if s != 'TN']
            if tm_count < n_tm_need and 'TM' in non_tn:
                assignments[emp.id] = 'TM'; tm_count += 1
            elif tt_count < n_tt_need and 'TT' in non_tn:
                assignments[emp.id] = 'TT'; tt_count += 1
            else:
                assignments[emp.id] = non_tn[0] if non_tn else allowed[0]

        for emp in employees:
            if emp.id in assignments:
                ShiftAssignment.objects.create(
                    employee=emp, year=year, month=month,
                    shift=assignments[emp.id], is_manual=False,
                )

        prev_shifts = {emp.id: assignments.get(emp.id) for emp in employees}

    return {}