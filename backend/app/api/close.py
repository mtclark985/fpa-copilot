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
    """Advance the simulation: generate actuals, calculate variances, run agents.

    Chain: simulate month → calculate variances → detection agent →
    attribution agent → proposal agent.
    """
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

    # Step 4: Try attribution agent
    try:
        from app.agents.variance_attributor import VarianceAttributorAgent
        attributor = VarianceAttributorAgent()
        attr_output = await attributor.analyze_period(session, next_period)
        summary["attributions_created"] = len(attr_output.attributions)
    except Exception as e:
        logger.warning("Attribution agent skipped: %s", e)
        summary["attributions_created"] = 0

    # Step 5: Try proposal agent
    try:
        from app.agents.proposal_generator import ProposalGeneratorAgent
        proposer = ProposalGeneratorAgent()
        prop_output = await proposer.generate_proposals(session, next_period)
        summary["proposals_created"] = len(prop_output.proposals)
    except Exception as e:
        logger.warning("Proposal agent skipped: %s", e)
        summary["proposals_created"] = 0

    return summary
