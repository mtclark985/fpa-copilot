"""Proposal decision service — handles accept/reject/modify logic.

Creates new ForecastVersion on accept, manages audit trail.
"""

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.forecast import ForecastLine, ForecastVersion
from app.models.proposal import ForecastProposal, ProposalDecisionAudit


async def accept_proposal(
    session: AsyncSession,
    proposal: ForecastProposal,
    note: str | None = None,
    modified_delta: float | None = None,
) -> ForecastVersion:
    """Accept a proposal (optionally with modified delta) and create a new ForecastVersion.

    Steps:
    1. Clone the current active ForecastVersion
    2. Apply the delta to matching cost_center × category × affected_periods
    3. Set old version inactive, new version active
    4. Update proposal status and linkage
    5. Create audit trail entry
    """
    # Determine effective delta
    effective_delta = modified_delta if modified_delta is not None else float(proposal.delta_per_period)

    # Determine new status
    if modified_delta is not None:
        new_status = "modified_and_accepted"
    else:
        new_status = "accepted"

    # Get current active forecast version
    fv_result = await session.execute(
        select(ForecastVersion)
        .where(ForecastVersion.is_active.is_(True))
        .order_by(ForecastVersion.id.desc())
        .limit(1)
    )
    old_version = fv_result.scalar_one()

    # Create new forecast version
    new_version = ForecastVersion(
        name=f"Forecast v{old_version.id + 1} — Proposal #{proposal.id} accepted",
        is_active=True,
        parent_version_id=old_version.id,
        source="proposal_accepted",
    )
    session.add(new_version)
    await session.flush()  # Get new_version.id

    # Clone all forecast lines from old version
    fl_result = await session.execute(
        select(ForecastLine).where(ForecastLine.version_id == old_version.id)
    )
    old_lines = list(fl_result.scalars().all())

    affected_periods_set = set(proposal.affected_periods)

    for old_line in old_lines:
        amount = float(old_line.amount)

        # Apply delta to matching lines
        if (old_line.cost_center_id == proposal.cost_center_id
                and old_line.category == proposal.category
                and old_line.period in affected_periods_set):
            amount += effective_delta

        new_line = ForecastLine(
            version_id=new_version.id,
            cost_center_id=old_line.cost_center_id,
            period=old_line.period,
            category=old_line.category,
            amount=round(amount, 2),
            headcount_eop=old_line.headcount_eop,
        )
        session.add(new_line)

    # Deactivate old version
    old_version.is_active = False

    # Update proposal
    proposal.status = new_status
    proposal.decided_at = datetime.datetime.utcnow()
    proposal.decided_by = "user"
    proposal.decision_note = note
    proposal.resulting_forecast_version_id = new_version.id
    if modified_delta is not None:
        proposal.modified_delta_per_period = modified_delta

    # Create audit entry
    delta_change = None
    if modified_delta is not None:
        delta_change = modified_delta - float(proposal.delta_per_period)

    audit = ProposalDecisionAudit(
        proposal_id=proposal.id,
        from_status="pending",
        to_status=new_status,
        note=note,
        delta_change=delta_change,
    )
    session.add(audit)

    await session.flush()
    await session.commit()

    return new_version


async def reject_proposal(
    session: AsyncSession,
    proposal: ForecastProposal,
    note: str | None = None,
) -> None:
    """Reject a proposal — no forecast version created."""
    proposal.status = "rejected"
    proposal.decided_at = datetime.datetime.utcnow()
    proposal.decided_by = "user"
    proposal.decision_note = note

    audit = ProposalDecisionAudit(
        proposal_id=proposal.id,
        from_status="pending",
        to_status="rejected",
        note=note,
    )
    session.add(audit)

    await session.flush()
    await session.commit()
