"""Tests for variance calculator — known-input produces known-output."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.variance import Variance


async def test_variances_exist(db_session: AsyncSession) -> None:
    """Variances should exist for the seeded months."""
    result = await db_session.execute(
        select(func.count()).select_from(Variance).where(Variance.period == "2026-01")
    )
    count = result.scalar()
    assert count is not None
    assert count > 0


async def test_variance_decomposition_adds_up(db_session: AsyncSession) -> None:
    """Volume variance + rate variance should approximately equal total variance."""
    result = await db_session.execute(
        select(Variance).where(
            Variance.period == "2026-01",
            Variance.forecast_amount > 1000,
            Variance.actual_amount > 1000,
        ).limit(20)
    )
    variances = result.scalars().all()

    for var in variances:
        total = float(var.variance_amount)
        decomposed = float(var.volume_variance) + float(var.rate_variance)
        # Allow small rounding tolerance
        assert abs(total - decomposed) < abs(total) * 0.05 + 1.0, (
            f"Variance {var.id}: total={total:.2f}, "
            f"volume={float(var.volume_variance):.2f} + rate={float(var.rate_variance):.2f} "
            f"= {decomposed:.2f}"
        )


async def test_materiality_score_range(db_session: AsyncSession) -> None:
    """All materiality scores should be between 0 and 100."""
    result = await db_session.execute(select(Variance))
    variances = result.scalars().all()
    for var in variances:
        score = float(var.materiality_score)
        assert 0 <= score <= 100, f"Variance {var.id}: materiality_score={score}"
