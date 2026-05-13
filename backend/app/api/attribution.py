"""Attribution API endpoints."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/attribution/{period}/run")
async def run_attribution(
    period: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str | int]:
    """Run the variance attribution agent for a period."""
    from app.agents.variance_attributor import VarianceAttributorAgent

    agent = VarianceAttributorAgent()
    output = await agent.analyze_period(session, period)
    return {
        "period": period,
        "attributions_created": len(output.attributions),
    }
