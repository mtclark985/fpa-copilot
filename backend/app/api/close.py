"""Close / advance-month API endpoint."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.actual import Actual
from app.seed.monthly_simulator import simulate_month
from app.services.variance_calculator import calculate_variances

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/close/advance-month")
async def advance_month(
    session: AsyncSession = Depends(get_session),
) -> dict[str, str | int]:
    """Advance the simulation: generate actuals, calculate variances, run agent."""
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

    # Step 1: Simulate month (generate actuals)
    summary = await simulate_month(session, next_period)

    # Step 2: Calculate variances
    variances = await calculate_variances(session, next_period)
    summary["variances_calculated"] = len(variances)

    # Step 3: Try agent analysis (may fail if no API key)
    try:
        from app.agents.variance_detector import VarianceDetectorAgent
        agent = VarianceDetectorAgent()
        assessment = await agent.analyze_period(session, next_period)
        summary["agent_assessments"] = len(assessment.assessments)
    except Exception as e:
        logger.warning("Agent analysis skipped: %s", e)
        summary["agent_assessments"] = 0

    return summary
