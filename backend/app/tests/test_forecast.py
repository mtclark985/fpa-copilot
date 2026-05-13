"""Test forecast engine math with known inputs."""

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cost_center import CostCenter
from app.models.employee import Employee
from app.models.forecast import ForecastLine, ForecastVersion
from app.services.forecast_engine import _monthly_fica, BENEFITS_LOAD


def test_fica_below_wage_base() -> None:
    """FICA on salary below the wage base uses the full rate."""
    result = _monthly_fica(120_000)
    expected = (120_000 / 12) * 0.0765
    assert abs(result - expected) < 0.01


def test_fica_above_wage_base() -> None:
    """FICA on salary above wage base caps SS, continues Medicare."""
    salary = 200_000
    monthly = salary / 12
    ss_monthly = (168_000 / 12) * 0.062
    medicare_monthly = monthly * 0.0145
    expected = ss_monthly + medicare_monthly
    result = _monthly_fica(salary)
    assert abs(result - expected) < 0.01


async def test_single_employee_forecast(db_session: AsyncSession) -> None:
    """One employee, projected 3 months, produces predictable numbers."""
    cc = CostCenter(code="TEST-FC", name="Test FC", vp_owner="Test VP")
    db_session.add(cc)
    await db_session.flush()

    emp = Employee(
        employee_number="E9999",
        name="Test Forecaster",
        hire_date=datetime.date(2025, 1, 1),
        cost_center_id=cc.id,
        job_level="L4",
        base_salary=120_000.00,
        bonus_target_pct=10.0,
        location="Charlotte",
    )
    db_session.add(emp)
    await db_session.flush()

    from app.services.forecast_engine import generate_forecast
    version = await generate_forecast(
        db_session,
        start_date=datetime.date(2026, 1, 1),
        months=3,
        version_name="Test FC",
    )

    result = await db_session.execute(
        select(ForecastLine).where(
            ForecastLine.version_id == version.id,
            ForecastLine.cost_center_id == cc.id,
            ForecastLine.period == "2026-01",
        )
    )
    lines = {line.category: float(line.amount) for line in result.scalars().all()}

    # January salary should be base/12
    expected_monthly_salary = 120_000 / 12
    assert abs(lines["salary"] - expected_monthly_salary) < 1.0

    # Benefits: 18% of base / 12
    expected_benefits = 120_000 * BENEFITS_LOAD / 12
    assert abs(lines["benefits"] - expected_benefits) < 1.0

    # Bonus: 10% of base / 12
    expected_bonus = 120_000 * 0.10 / 12
    assert abs(lines["bonus"] - expected_bonus) < 1.0
