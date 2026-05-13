"""Proposal API endpoints."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/proposals/{period}/generate")
async def generate_proposals(
    period: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str | int]:
    """Run the proposal generator agent for a period."""
    from app.agents.proposal_generator import ProposalGeneratorAgent

    agent = ProposalGeneratorAgent()
    output = await agent.generate_proposals(session, period)
    return {
        "period": period,
        "proposals_created": len(output.proposals),
    }
