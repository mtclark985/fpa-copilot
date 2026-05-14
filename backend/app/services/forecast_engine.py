"""Driver-based compensation expense forecast engine.

Generates an 18-month forecast from the seeded company data using
these drivers: baseline roll-forward, merit cycle, planned hires,
attrition, bonus accrual, benefits load, and payroll taxes.
"""

import datetime
import random
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cost_center import CostCenter
from app.models.employee import Employee
from app.models.forecast import ForecastLine, ForecastVersion
from app.models.position import Position
from app.services.forecast_assumptions import DEFAULT_ASSUMPTIONS, ForecastAssumptions


def _monthly_fica(annual_salary: float, assumptions: ForecastAssumptions) -> float:
    """Calculate monthly employer FICA cost for a given annual salary."""
    monthly = annual_salary / 12
    if annual_salary <= assumptions.fica_wage_base:
        return monthly * assumptions.fica_rate
    else:
        # SS portion capped, Medicare continues
        ss_monthly = (assumptions.fica_wage_base / 12) * 0.062
        medicare_monthly = monthly * assumptions.medicare_only_rate
        return ss_monthly + medicare_monthly


async def generate_forecast(
    session: AsyncSession,
    start_date: datetime.date = datetime.date(2026, 1, 1),
    months: int = 18,
    version_name: str = "Initial Plan FY26",
    assumptions: ForecastAssumptions | None = None,
) -> ForecastVersion:
    """Build a full driver-based forecast and persist it.

    Returns the created ForecastVersion with all lines attached.
    """
    if assumptions is None:
        assumptions = DEFAULT_ASSUMPTIONS

    random.seed(42)

    # Load current state
    employees_result = await session.execute(
        select(Employee).where(Employee.termination_date.is_(None))
    )
    employees = list(employees_result.scalars().all())

    positions_result = await session.execute(
        select(Position).where(Position.status == "open")
    )
    open_positions = list(positions_result.scalars().all())

    cc_result = await session.execute(select(CostCenter))
    cost_centers = {cc.id: cc for cc in cc_result.scalars().all()}

    # Create forecast version
    version = ForecastVersion(name=version_name, is_active=True)
    session.add(version)
    await session.flush()

    # Build month-by-month forecast
    # Track headcount per cost center per month
    # Start with current employees grouped by cost center
    cc_employees: dict[int, list[dict[str, float | str | int]]] = defaultdict(list)
    for emp in employees:
        cc_employees[emp.cost_center_id].append({
            "salary": float(emp.base_salary),
            "bonus_pct": float(emp.bonus_target_pct),
            "level": emp.job_level,
        })

    # Pre-calculate which open positions land in which month
    position_by_month: dict[str, list[dict[str, float | str | int]]] = defaultdict(list)
    from app.seed.company_generator import COMP_BANDS, BONUS_TARGETS
    for pos in open_positions:
        period = pos.target_start_date.strftime("%Y-%m")
        mid_salary = sum(COMP_BANDS[pos.job_level]) / 2
        position_by_month[period].append({
            "cost_center_id": pos.cost_center_id,
            "salary": mid_salary,
            "bonus_pct": BONUS_TARGETS[pos.job_level],
            "level": pos.job_level,
        })

    # Per-month aggregation
    lines: list[ForecastLine] = []

    for month_offset in range(months):
        year = start_date.year + (start_date.month + month_offset - 1) // 12
        month = (start_date.month + month_offset - 1) % 12 + 1
        period = f"{year:04d}-{month:02d}"

        # Apply merit cycle in April
        if month == assumptions.merit_month:
            for cc_id in cc_employees:
                for emp_data in cc_employees[cc_id]:
                    merit = random.gauss(assumptions.merit_avg_pct, 0.01)
                    merit = max(0.0, min(0.08, merit))  # clamp 0-8%
                    emp_data["salary"] = float(emp_data["salary"]) * (1 + merit)

        # Add planned hires from open positions
        for pos_data in position_by_month.get(period, []):
            cc_id = int(pos_data["cost_center_id"])
            cc_employees[cc_id].append({
                "salary": pos_data["salary"],
                "bonus_pct": pos_data["bonus_pct"],
                "level": pos_data["level"],
            })

        # Add growth hires (2% of headcount per quarter, evenly across 3 months)
        if month % 3 == 1:  # first month of quarter
            total_hc = sum(len(emps) for emps in cc_employees.values())
            new_hires = max(1, int(total_hc * assumptions.quarterly_hire_growth / 3))
            # Distribute across cost centers proportionally
            cc_ids = [cc_id for cc_id in cc_employees if cc_employees[cc_id]]
            for _ in range(new_hires):
                target_cc = random.choice(cc_ids)
                level = random.choice(["L3", "L4", "L5"])
                mid_salary = sum(COMP_BANDS[level]) / 2
                cc_employees[target_cc].append({
                    "salary": mid_salary,
                    "bonus_pct": BONUS_TARGETS[level],
                    "level": level,
                })

        # Apply monthly attrition
        monthly_attrition = assumptions.annual_attrition_rate / 12
        for cc_id in list(cc_employees.keys()):
            emps = cc_employees[cc_id]
            departures = int(len(emps) * monthly_attrition)
            if departures > 0 and len(emps) > departures:
                for _ in range(departures):
                    idx = random.randint(0, len(emps) - 1)
                    emps.pop(idx)

        # Aggregate by cost center
        for cc_id, emps in cc_employees.items():
            if cc_id not in cost_centers:
                continue

            total_salary = sum(float(e["salary"]) / 12 for e in emps)
            total_benefits = sum(float(e["salary"]) * assumptions.benefits_load_pct / 12 for e in emps)
            total_taxes = sum(_monthly_fica(float(e["salary"]), assumptions) for e in emps)

            # Bonus: accrued monthly, target % of salary
            total_bonus = sum(
                float(e["salary"]) * float(e["bonus_pct"]) / 100 / 12 for e in emps
            )

            headcount = len(emps)

            for category, amount in [
                ("salary", total_salary),
                ("bonus", total_bonus),
                ("benefits", total_benefits),
                ("taxes", total_taxes),
            ]:
                line = ForecastLine(
                    version_id=version.id,
                    cost_center_id=cc_id,
                    period=period,
                    category=category,
                    amount=round(amount, 2),
                    headcount_eop=headcount,
                )
                lines.append(line)

    session.add_all(lines)
    await session.flush()
    await session.commit()

    return version
