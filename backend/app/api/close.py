"""Close / advance-month API endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.actual import Actual
from app.seed.monthly_simulator import simulate_month

router = APIRouter()


@router.post("/close/advance-month")
async def advance_month(
    session: AsyncSession = Depends(get_session),
) -> dict[str, str | int]:
    """Advance the simulation by one month, generating actuals."""
    # Determine next period
    result = await session.execute(select(func.max(Actual.period)))
    latest = result.scalar()

    if latest is None:
        next_period = "2026-01"
    else:
        year, month = int(latest[:4]), int(latest[5:7])
        if month == 12:
            next_period = f"{year + 1:04d}-01"
        else:
            next_period = f"{year:04d}-{month + 1:02d}"

    summary = await simulate_month(session, next_period)
    return summary
