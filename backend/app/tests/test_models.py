"""Test that ORM models can be created, persisted, and queried."""

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Actual,
    CostCenter,
    Employee,
    ForecastLine,
    ForecastVersion,
    Position,
    Variance,
)


async def test_cost_center_crud(db_session: AsyncSession) -> None:
    """Cost center can be created and queried."""
    cc = CostCenter(code="ENG-001", name="Platform Engineering", vp_owner="Jane Smith")
    db_session.add(cc)
    await db_session.flush()

    result = await db_session.execute(select(CostCenter).where(CostCenter.code == "ENG-001"))
    fetched = result.scalar_one()
    assert fetched.name == "Platform Engineering"
    assert fetched.vp_owner == "Jane Smith"


async def test_employee_with_cost_center(db_session: AsyncSession) -> None:
    """Employee links to its cost center via FK."""
    cc = CostCenter(code="FIN-001", name="Finance", vp_owner="Bob Jones")
    db_session.add(cc)
    await db_session.flush()

    emp = Employee(
        employee_number="E0001",
        name="Alice Analyst",
        hire_date=datetime.date(2023, 6, 15),
        cost_center_id=cc.id,
        job_level="L4",
        base_salary=95000.00,
        bonus_target_pct=10.0,
        location="Charlotte",
    )
    db_session.add(emp)
    await db_session.flush()

    result = await db_session.execute(select(Employee).where(Employee.id == emp.id))
    fetched = result.scalar_one()
    assert fetched.cost_center_id == cc.id
    assert float(fetched.base_salary) == 95000.00


async def test_position_model(db_session: AsyncSession) -> None:
    """Position can be created with open status."""
    cc = CostCenter(code="MKT-001", name="Marketing", vp_owner="Carol Lee")
    db_session.add(cc)
    await db_session.flush()

    pos = Position(
        cost_center_id=cc.id,
        job_level="L5",
        status="open",
        target_start_date=datetime.date(2026, 3, 1),
    )
    db_session.add(pos)
    await db_session.flush()

    result = await db_session.execute(select(Position).where(Position.status == "open"))
    fetched = result.scalar_one()
    assert fetched.job_level == "L5"


async def test_forecast_version_and_lines(db_session: AsyncSession) -> None:
    """Forecast version with lines can be created and queried."""
    cc = CostCenter(code="HR-001", name="HR", vp_owner="Dan White")
    db_session.add(cc)
    await db_session.flush()

    fv = ForecastVersion(name="Initial Plan FY26", is_active=True)
    db_session.add(fv)
    await db_session.flush()

    line = ForecastLine(
        version_id=fv.id,
        cost_center_id=cc.id,
        period="2026-01",
        category="salary",
        amount=500000.00,
        headcount_eop=50,
    )
    db_session.add(line)
    await db_session.flush()

    result = await db_session.execute(
        select(ForecastLine).where(ForecastLine.version_id == fv.id)
    )
    fetched = result.scalar_one()
    assert fetched.period == "2026-01"
    assert float(fetched.amount) == 500000.00


async def test_actual_model(db_session: AsyncSession) -> None:
    """Actual expense can be linked to an employee."""
    cc = CostCenter(code="OPS-001", name="Operations", vp_owner="Eve Black")
    db_session.add(cc)
    await db_session.flush()

    emp = Employee(
        employee_number="E0099",
        name="Test Worker",
        hire_date=datetime.date(2024, 1, 1),
        cost_center_id=cc.id,
        job_level="L3",
        base_salary=75000.00,
        bonus_target_pct=8.0,
        location="Remote",
    )
    db_session.add(emp)
    await db_session.flush()

    actual = Actual(
        employee_id=emp.id,
        period="2026-01",
        category="salary",
        amount=6250.00,
    )
    db_session.add(actual)
    await db_session.flush()

    result = await db_session.execute(select(Actual).where(Actual.employee_id == emp.id))
    fetched = result.scalar_one()
    assert float(fetched.amount) == 6250.00


async def test_variance_model(db_session: AsyncSession) -> None:
    """Variance record stores both calculated and agent fields."""
    cc = CostCenter(code="SLS-001", name="Sales", vp_owner="Frank Green")
    db_session.add(cc)
    await db_session.flush()

    fv = ForecastVersion(name="Test Plan", is_active=False)
    db_session.add(fv)
    await db_session.flush()

    var = Variance(
        forecast_version_id=fv.id,
        cost_center_id=cc.id,
        period="2026-01",
        category="salary",
        forecast_amount=100000.00,
        actual_amount=105000.00,
        variance_amount=5000.00,
        variance_pct=5.0,
        volume_variance=3000.00,
        rate_variance=2000.00,
        materiality_score=65.0,
        agent_severity="medium",
        agent_rationale="Unplanned hire",
    )
    db_session.add(var)
    await db_session.flush()

    result = await db_session.execute(select(Variance).where(Variance.id == var.id))
    fetched = result.scalar_one()
    assert fetched.agent_severity == "medium"
    assert float(fetched.variance_amount) == 5000.00
