"""Smoke tests for the demo company seeder.

These tests run against the live database after seeding,
so they verify the actual seeded data.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cost_center import CostCenter
from app.models.employee import Employee
from app.models.position import Position


async def test_employee_count(db_session: AsyncSession) -> None:
    """Total employees is at least 500 (seed) plus simulator additions."""
    result = await db_session.execute(select(func.count()).select_from(Employee))
    count = result.scalar()
    assert count is not None
    assert count >= 500  # base seed is 500; simulator adds more


async def test_cost_center_count(db_session: AsyncSession) -> None:
    """Seeder produces the expected number of cost centers."""
    result = await db_session.execute(select(func.count()).select_from(CostCenter))
    count = result.scalar()
    assert count is not None
    assert count >= 20  # at least 20 as spec requires


async def test_open_positions_count(db_session: AsyncSession) -> None:
    """Seeder produces roughly 25 open positions."""
    result = await db_session.execute(
        select(func.count()).select_from(Position).where(Position.status == "open")
    )
    count = result.scalar()
    assert count is not None
    assert 15 <= count <= 50


async def test_every_employee_has_cost_center(db_session: AsyncSession) -> None:
    """No employee exists without a valid cost center."""
    result = await db_session.execute(
        select(func.count())
        .select_from(Employee)
        .where(Employee.cost_center_id.is_(None))
    )
    assert result.scalar() == 0


async def test_comp_within_bands(db_session: AsyncSession) -> None:
    """Seeded employees' salaries fall within their level's band (with COL adjustment).

    Only checks originally seeded employees (E0001-E0500), not simulator-generated
    hires which may have salary premiums.
    """
    bands = {
        "L3": (70_000 * 0.85, 100_000 * 1.25),
        "L4": (95_000 * 0.85, 135_000 * 1.25),
        "L5": (125_000 * 0.85, 180_000 * 1.25),
        "L6": (165_000 * 0.85, 240_000 * 1.25),
        "L7": (220_000 * 0.85, 320_000 * 1.25),
    }
    result = await db_session.execute(
        select(Employee).where(Employee.employee_number.like("E0%"))
    )
    employees = result.scalars().all()
    assert len(employees) >= 500
    for emp in employees:
        low, high = bands[emp.job_level]
        salary = float(emp.base_salary)
        assert low <= salary <= high, (
            f"{emp.employee_number} ({emp.job_level}): ${salary:,.0f} "
            f"outside [{low:,.0f}, {high:,.0f}]"
        )
