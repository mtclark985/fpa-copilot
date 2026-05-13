"""Tests for the monthly simulator — determinism and business rules."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.actual import Actual


async def test_actuals_exist_for_jan(db_session: AsyncSession) -> None:
    """After seeding, January 2026 should have actuals."""
    result = await db_session.execute(
        select(func.count()).select_from(Actual).where(Actual.period == "2026-01")
    )
    count = result.scalar()
    assert count is not None
    assert count > 0, "Expected actuals for 2026-01 after seed + simulate"


async def test_actuals_have_four_categories(db_session: AsyncSession) -> None:
    """Each period should have salary, bonus, benefits, taxes actuals."""
    result = await db_session.execute(
        select(Actual.category).where(Actual.period == "2026-01").distinct()
    )
    categories = {row[0] for row in result.all()}
    assert categories == {"salary", "bonus", "benefits", "taxes"}


async def test_six_months_of_actuals(db_session: AsyncSession) -> None:
    """After 6 simulate runs, we should have 6 distinct periods."""
    result = await db_session.execute(
        select(func.count(func.distinct(Actual.period)))
    )
    count = result.scalar()
    assert count == 6
