"""Monthly payroll simulator — generates realistic actuals with intentional variances.

Each month advance generates payroll for all active employees and introduces
deviations from forecast: unplanned hires/departures, retention bonuses,
and one narrative "story" variance per month.
"""

import datetime
import random

from faker import Faker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.actual import Actual
from app.models.cost_center import CostCenter
from app.models.employee import Employee
from app.seed.company_generator import BONUS_TARGETS, COMP_BANDS, _pick_location

fake = Faker()

# Story variances — one per month, these create the interesting narratives
STORY_VARIANCES: dict[str, dict[str, str | int]] = {
    "2026-01": {
        "story": "Risk team backfilled 3 open positions early at above-market rates",
        "cc_code_prefix": "CORP",
        "extra_hires": 3,
        "salary_premium_pct": 15,
    },
    "2026-02": {
        "story": "Engineering retention bonuses paid to 5 senior engineers",
        "cc_code_prefix": "TECH",
        "retention_bonuses": 5,
        "bonus_amount": 25_000,
    },
    "2026-03": {
        "story": "Sales team had 4 unplanned departures due to competitor poaching",
        "cc_code_prefix": "GTM-SLS",
        "extra_departures": 4,
    },
    "2026-04": {
        "story": "Platform Engineering hired a new team lead at L7 for cloud migration",
        "cc_code_prefix": "TECH-PLAT",
        "extra_hires": 1,
        "hire_level": "L7",
    },
    "2026-05": {
        "story": "Company-wide off-cycle adjustment: 2% COLA for Charlotte employees",
        "cc_code_prefix": "ALL",
        "cola_pct": 2,
        "cola_location": "Charlotte",
    },
    "2026-06": {
        "story": "Customer Success expanded with 4 new hires ahead of product launch",
        "cc_code_prefix": "GTM-CS",
        "extra_hires": 4,
    },
    "2026-07": {
        "story": "Data Engineering contractor conversions: 3 contractors became FTEs",
        "cc_code_prefix": "TECH-DATA",
        "extra_hires": 3,
    },
    "2026-08": {
        "story": "Marketing reduced headcount by 3 after campaign strategy shift",
        "cc_code_prefix": "GTM-MKT",
        "extra_departures": 3,
    },
    "2026-09": {
        "story": "Finance team overtime during audit season, 20% salary premium",
        "cc_code_prefix": "CORP-FIN",
        "overtime_pct": 20,
    },
    "2026-10": {
        "story": "Mobile team rapid expansion: 5 hires for new product line",
        "cc_code_prefix": "TECH-PROD",
        "extra_hires": 5,
    },
    "2026-11": {
        "story": "HR reorganization: 2 senior departures, replaced with junior hires",
        "cc_code_prefix": "CORP-HR",
        "extra_departures": 2,
        "extra_hires": 2,
        "hire_level": "L3",
    },
    "2026-12": {
        "story": "Year-end spot bonuses for top performers across Engineering",
        "cc_code_prefix": "TECH",
        "spot_bonuses": 10,
        "bonus_amount": 10_000,
    },
}

BENEFITS_LOAD = 0.18
FICA_WAGE_BASE = 168_000
FICA_RATE = 0.0765
MEDICARE_ONLY_RATE = 0.0145


def _monthly_fica(annual_salary: float) -> float:
    """Calculate monthly employer FICA."""
    monthly = annual_salary / 12
    if annual_salary <= FICA_WAGE_BASE:
        return monthly * FICA_RATE
    else:
        ss_monthly = (FICA_WAGE_BASE / 12) * 0.062
        medicare_monthly = monthly * MEDICARE_ONLY_RATE
        return ss_monthly + medicare_monthly


async def _get_cost_centers_by_prefix(
    session: AsyncSession, prefix: str
) -> list[CostCenter]:
    """Get cost centers matching a code prefix."""
    if prefix == "ALL":
        result = await session.execute(select(CostCenter))
    else:
        result = await session.execute(
            select(CostCenter).where(CostCenter.code.startswith(prefix))
        )
    return list(result.scalars().all())


async def simulate_month(
    session: AsyncSession,
    period: str,
    seed: int = 42,
) -> dict[str, str | int]:
    """Simulate one month of payroll actuals with realistic variances.

    Returns a summary of what happened this month.
    """
    random.seed(seed + hash(period))
    Faker.seed(seed + hash(period))

    year, month = int(period[:4]), int(period[5:7])
    period_start = datetime.date(year, month, 1)
    if month == 12:
        period_end = datetime.date(year, 12, 31)
    else:
        period_end = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)

    # Load active employees (hired before period end, not terminated before period start)
    result = await session.execute(
        select(Employee).where(
            Employee.hire_date <= period_end,
            (Employee.termination_date.is_(None)) | (Employee.termination_date > period_start),
        )
    )
    active_employees = list(result.scalars().all())

    actuals_created = 0
    events: list[str] = []

    # Step 1: Apply story variance for this month
    story_data = STORY_VARIANCES.get(period, {})
    story = str(story_data.get("story", "Normal month"))

    if "extra_hires" in story_data:
        cc_prefix = str(story_data["cc_code_prefix"])
        target_ccs = await _get_cost_centers_by_prefix(session, cc_prefix)
        hire_level = str(story_data.get("hire_level", "L4"))
        num_hires = int(story_data["extra_hires"])
        premium = int(story_data.get("salary_premium_pct", 0))

        for i in range(num_hires):
            cc = random.choice(target_ccs) if target_ccs else None
            if cc is None:
                continue
            location, col_mult = _pick_location()
            low, high = COMP_BANDS[hire_level]
            base_salary = round(random.randint(low, high) * col_mult * (1 + premium / 100) / 1000) * 1000

            emp = Employee(
                employee_number=f"E{9000 + hash(period) % 1000 + i:04d}",
                name=fake.name(),
                hire_date=period_start + datetime.timedelta(days=random.randint(0, 15)),
                cost_center_id=cc.id,
                job_level=hire_level,
                base_salary=base_salary,
                bonus_target_pct=BONUS_TARGETS[hire_level],
                location=location,
            )
            session.add(emp)
            active_employees.append(emp)
        events.append(f"Hired {num_hires} (story)")

    if "extra_departures" in story_data:
        cc_prefix = str(story_data["cc_code_prefix"])
        target_ccs = await _get_cost_centers_by_prefix(session, cc_prefix)
        cc_ids = {cc.id for cc in target_ccs}
        num_deps = int(story_data["extra_departures"])

        eligible = [e for e in active_employees if e.cost_center_id in cc_ids and e.termination_date is None]
        departures = random.sample(eligible, min(num_deps, len(eligible)))
        for emp in departures:
            emp.termination_date = period_start + datetime.timedelta(days=random.randint(1, 28))
        events.append(f"Terminated {len(departures)} (story)")

    if "cola_pct" in story_data:
        cola = int(story_data["cola_pct"]) / 100
        loc = str(story_data["cola_location"])
        adjusted = 0
        for emp in active_employees:
            if emp.location == loc and emp.termination_date is None:
                emp.base_salary = float(emp.base_salary) * (1 + cola)
                adjusted += 1
        events.append(f"COLA {cola*100:.0f}% for {adjusted} {loc} employees")

    await session.flush()

    # Step 2: Random unplanned hires (1-2 per month)
    num_random_hires = random.randint(1, 2)
    all_ccs_result = await session.execute(select(CostCenter))
    all_ccs = list(all_ccs_result.scalars().all())

    for i in range(num_random_hires):
        cc = random.choice(all_ccs)
        level = random.choice(["L3", "L4", "L5"])
        location, col_mult = _pick_location()
        low, high = COMP_BANDS[level]
        salary = round(random.randint(low, high) * col_mult / 1000) * 1000

        emp = Employee(
            employee_number=f"E{8000 + hash(period) % 1000 + i:04d}",
            name=fake.name(),
            hire_date=period_start + datetime.timedelta(days=random.randint(0, 28)),
            cost_center_id=cc.id,
            job_level=level,
            base_salary=salary,
            bonus_target_pct=BONUS_TARGETS[level],
            location=location,
        )
        session.add(emp)
        active_employees.append(emp)
    events.append(f"Hired {num_random_hires} (random)")

    # Step 3: Random unplanned departures (1-2 per month)
    num_random_deps = random.randint(1, 2)
    eligible_for_term = [
        e for e in active_employees
        if e.termination_date is None and (period_start - e.hire_date).days > 90
    ]
    departures = random.sample(eligible_for_term, min(num_random_deps, len(eligible_for_term)))
    for emp in departures:
        emp.termination_date = period_start + datetime.timedelta(days=random.randint(1, 28))
    events.append(f"Terminated {len(departures)} (random)")

    await session.flush()

    # Step 4: Generate payroll actuals for all active employees this period
    # Reload active employees after changes
    result = await session.execute(
        select(Employee).where(
            Employee.hire_date <= period_end,
            (Employee.termination_date.is_(None)) | (Employee.termination_date > period_start),
        )
    )
    payroll_employees = list(result.scalars().all())

    for emp in payroll_employees:
        salary = float(emp.base_salary)
        monthly_salary = salary / 12
        monthly_benefits = salary * BENEFITS_LOAD / 12
        monthly_taxes = _monthly_fica(salary)
        monthly_bonus = salary * float(emp.bonus_target_pct) / 100 / 12

        # Small random noise on actuals (±2%) to simulate real payroll variance
        noise = random.uniform(0.98, 1.02)

        for category, amount in [
            ("salary", monthly_salary * noise),
            ("benefits", monthly_benefits * noise),
            ("taxes", monthly_taxes * noise),
            ("bonus", monthly_bonus * noise),
        ]:
            actual = Actual(
                employee_id=emp.id,
                period=period,
                category=category,
                amount=round(amount, 2),
            )
            session.add(actual)
            actuals_created += 1

    # Step 5: Add story-specific actuals (retention/spot bonuses, overtime)
    if "retention_bonuses" in story_data or "spot_bonuses" in story_data:
        cc_prefix = str(story_data["cc_code_prefix"])
        target_ccs = await _get_cost_centers_by_prefix(session, cc_prefix)
        cc_ids = {cc.id for cc in target_ccs}
        num_bonuses = int(story_data.get("retention_bonuses", story_data.get("spot_bonuses", 0)))
        bonus_amt = int(story_data["bonus_amount"])

        eligible = [e for e in payroll_employees if e.cost_center_id in cc_ids]
        recipients = random.sample(eligible, min(num_bonuses, len(eligible)))
        for emp in recipients:
            actual = Actual(
                employee_id=emp.id,
                period=period,
                category="bonus",
                amount=bonus_amt,
            )
            session.add(actual)
            actuals_created += 1
        events.append(f"Paid {len(recipients)} bonuses of ${bonus_amt:,}")

    if "overtime_pct" in story_data:
        cc_prefix = str(story_data["cc_code_prefix"])
        target_ccs = await _get_cost_centers_by_prefix(session, cc_prefix)
        cc_ids = {cc.id for cc in target_ccs}
        ot_pct = int(story_data["overtime_pct"]) / 100

        for emp in payroll_employees:
            if emp.cost_center_id in cc_ids:
                ot_amount = float(emp.base_salary) / 12 * ot_pct
                actual = Actual(
                    employee_id=emp.id,
                    period=period,
                    category="salary",
                    amount=round(ot_amount, 2),
                )
                session.add(actual)
                actuals_created += 1
        events.append(f"Overtime premium for {cc_prefix}")

    await session.flush()
    await session.commit()

    return {
        "period": period,
        "story": story,
        "actuals_created": actuals_created,
        "events": ", ".join(events),
    }
