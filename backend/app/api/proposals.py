"""Proposal API endpoints — CRUD and decision actions."""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.attribution import AttributionRecord
from app.models.cost_center import CostCenter
from app.models.proposal import ForecastProposal
from app.models.variance import Variance
from app.schemas.proposal import (
    DecisionRequest,
    ModifyAndAcceptRequest,
    ProposalDetailSchema,
    ProposalSchema,
)
from app.services.proposal_service import accept_proposal, reject_proposal

logger = logging.getLogger(__name__)

router = APIRouter()


def _proposal_to_schema(proposal: ForecastProposal, cc_name: str) -> ProposalSchema:
    """Convert a ForecastProposal ORM object to a ProposalSchema."""
    return ProposalSchema(
        id=proposal.id,
        created_at=proposal.created_at.isoformat() if proposal.created_at else "",
        created_for_period=proposal.created_for_period,
        status=proposal.status,
        cost_center_id=proposal.cost_center_id,
        cost_center_name=cc_name,
        category=proposal.category,
        affected_periods=proposal.affected_periods or [],
        delta_per_period=float(proposal.delta_per_period),
        agent_rationale=proposal.agent_rationale,
        driving_variance_ids=proposal.driving_variance_ids or [],
        attributed_events=proposal.attributed_events or [],
        confidence=proposal.confidence,
        decided_at=proposal.decided_at.isoformat() if proposal.decided_at else None,
        decided_by=proposal.decided_by,
        decision_note=proposal.decision_note,
        modified_delta_per_period=(
            float(proposal.modified_delta_per_period)
            if proposal.modified_delta_per_period is not None
            else None
        ),
        resulting_forecast_version_id=proposal.resulting_forecast_version_id,
    )


@router.get("/proposals", response_model=list[ProposalSchema])
async def list_proposals(
    session: AsyncSession = Depends(get_session),
    status: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    cost_center_id: Optional[int] = Query(None),
) -> list[ProposalSchema]:
    """List proposals with optional filters."""
    query = (
        select(ForecastProposal, CostCenter.name)
        .join(CostCenter, ForecastProposal.cost_center_id == CostCenter.id)
    )

    if status:
        query = query.where(ForecastProposal.status == status)
    if period:
        query = query.where(ForecastProposal.created_for_period == period)
    if cost_center_id:
        query = query.where(ForecastProposal.cost_center_id == cost_center_id)

    query = query.order_by(ForecastProposal.id.desc())
    result = await session.execute(query)

    return [
        _proposal_to_schema(proposal, cc_name)
        for proposal, cc_name in result.all()
    ]


@router.get("/proposals/{proposal_id}", response_model=ProposalDetailSchema)
async def get_proposal_detail(
    proposal_id: int,
    session: AsyncSession = Depends(get_session),
) -> ProposalDetailSchema:
    """Get full proposal detail including driving variances and attributions."""
    result = await session.execute(
        select(ForecastProposal, CostCenter.name)
        .join(CostCenter, ForecastProposal.cost_center_id == CostCenter.id)
        .where(ForecastProposal.id == proposal_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    proposal, cc_name = row
    base = _proposal_to_schema(proposal, cc_name)

    # Fetch driving variances
    driving_variances: list[Any] = []
    if proposal.driving_variance_ids:
        var_result = await session.execute(
            select(Variance, CostCenter.name)
            .join(CostCenter, Variance.cost_center_id == CostCenter.id)
            .where(Variance.id.in_(proposal.driving_variance_ids))
        )
        for var, var_cc_name in var_result.all():
            driving_variances.append({
                "id": var.id,
                "cost_center_name": var_cc_name,
                "category": var.category,
                "period": var.period,
                "variance_amount": float(var.variance_amount),
                "variance_pct": float(var.variance_pct),
                "materiality_score": float(var.materiality_score),
                "agent_severity": var.agent_severity,
                "agent_rationale": var.agent_rationale,
            })

    # Fetch attribution records for the driving variances
    attribution_records: list[Any] = []
    if proposal.driving_variance_ids:
        attr_result = await session.execute(
            select(AttributionRecord)
            .where(AttributionRecord.variance_id.in_(proposal.driving_variance_ids))
        )
        for attr in attr_result.scalars().all():
            attribution_records.append({
                "id": attr.id,
                "variance_id": attr.variance_id,
                "attribution_type": attr.attribution_type,
                "narrative": attr.narrative,
                "structured_drivers": attr.structured_drivers,
                "confidence": attr.confidence,
            })

    return ProposalDetailSchema(
        **base.model_dump(),
        driving_variances=driving_variances,
        attribution_records=attribution_records,
    )


@router.post("/proposals/{proposal_id}/accept")
async def accept_proposal_endpoint(
    proposal_id: int,
    body: DecisionRequest = DecisionRequest(),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Accept a proposal — creates a new ForecastVersion with the delta applied."""
    proposal = await session.get(ForecastProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status != "pending":
        raise HTTPException(status_code=400, detail=f"Proposal is already {proposal.status}")

    new_version = await accept_proposal(session, proposal, note=body.note)
    return {
        "proposal_id": proposal.id,
        "status": proposal.status,
        "new_forecast_version_id": new_version.id,
    }


@router.post("/proposals/{proposal_id}/reject")
async def reject_proposal_endpoint(
    proposal_id: int,
    body: DecisionRequest = DecisionRequest(),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str | int]:
    """Reject a proposal — no forecast change."""
    proposal = await session.get(ForecastProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status != "pending":
        raise HTTPException(status_code=400, detail=f"Proposal is already {proposal.status}")

    await reject_proposal(session, proposal, note=body.note)
    return {
        "proposal_id": proposal.id,
        "status": proposal.status,
    }


@router.post("/proposals/{proposal_id}/modify-and-accept")
async def modify_and_accept_endpoint(
    proposal_id: int,
    body: ModifyAndAcceptRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Modify the delta and accept — creates new ForecastVersion with modified delta."""
    proposal = await session.get(ForecastProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status != "pending":
        raise HTTPException(status_code=400, detail=f"Proposal is already {proposal.status}")

    new_version = await accept_proposal(
        session, proposal,
        note=body.note,
        modified_delta=body.modified_delta_per_period,
    )
    return {
        "proposal_id": proposal.id,
        "status": proposal.status,
        "new_forecast_version_id": new_version.id,
    }


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
