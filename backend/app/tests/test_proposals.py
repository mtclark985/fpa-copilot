"""Tests for proposal service — accept/reject/modify logic."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CostCenter,
    ForecastLine,
    ForecastProposal,
    ForecastVersion,
    ProposalDecisionAudit,
)
from app.services.proposal_service import accept_proposal, reject_proposal


def _uid() -> str:
    return uuid.uuid4().hex[:8]


async def _create_test_proposal(
    session: AsyncSession,
) -> tuple[ForecastProposal, ForecastVersion]:
    """Helper to create a test proposal with a forecast version to work against."""
    cc = CostCenter(code=f"TEST-{_uid()}", name="Test CC", vp_owner="Test Owner")
    session.add(cc)
    await session.flush()

    fv = ForecastVersion(name=f"Test Plan {_uid()}", is_active=True, source="initial_plan")
    session.add(fv)
    await session.flush()

    # Create forecast lines for the cost center
    for period in ["2026-07", "2026-08", "2026-09"]:
        line = ForecastLine(
            version_id=fv.id,
            cost_center_id=cc.id,
            period=period,
            category="salary",
            amount=50000.00,
            headcount_eop=10,
        )
        session.add(line)

    await session.flush()

    proposal = ForecastProposal(
        created_for_period="2026-06",
        status="pending",
        cost_center_id=cc.id,
        category="salary",
        affected_periods=["2026-07", "2026-08", "2026-09"],
        delta_per_period=5000.00,
        agent_rationale="Test rationale for salary increase.",
        driving_variance_ids=[],
        attributed_events=[],
        confidence="high",
    )
    session.add(proposal)
    await session.flush()

    return proposal, fv


async def test_accept_proposal_creates_new_version(db_session: AsyncSession) -> None:
    """Accepting a proposal creates a new active ForecastVersion."""
    proposal, old_version = await _create_test_proposal(db_session)

    new_version = await accept_proposal(db_session, proposal, note="Looks good")

    assert new_version.is_active is True
    assert new_version.parent_version_id == old_version.id
    assert new_version.source == "proposal_accepted"
    assert proposal.status == "accepted"
    assert proposal.resulting_forecast_version_id == new_version.id

    # Old version should be inactive
    result = await db_session.execute(
        select(ForecastVersion).where(ForecastVersion.id == old_version.id)
    )
    refreshed_old = result.scalar_one()
    assert refreshed_old.is_active is False


async def test_accept_proposal_applies_delta(db_session: AsyncSession) -> None:
    """Accepted proposal applies delta to matching forecast lines."""
    proposal, old_version = await _create_test_proposal(db_session)

    new_version = await accept_proposal(db_session, proposal)

    # Check new version's forecast lines
    result = await db_session.execute(
        select(ForecastLine).where(
            ForecastLine.version_id == new_version.id,
            ForecastLine.cost_center_id == proposal.cost_center_id,
            ForecastLine.category == "salary",
        )
    )
    new_lines = list(result.scalars().all())

    assert len(new_lines) == 3
    for line in new_lines:
        # Original was 50000, delta is 5000
        assert float(line.amount) == 55000.00


async def test_reject_proposal(db_session: AsyncSession) -> None:
    """Rejecting a proposal changes status, creates no forecast version."""
    proposal, _ = await _create_test_proposal(db_session)

    await reject_proposal(db_session, proposal, note="Not warranted")

    assert proposal.status == "rejected"
    assert proposal.resulting_forecast_version_id is None
    assert proposal.decision_note == "Not warranted"


async def test_modify_and_accept(db_session: AsyncSession) -> None:
    """Modify-and-accept uses the modified delta."""
    proposal, old_version = await _create_test_proposal(db_session)

    new_version = await accept_proposal(
        db_session, proposal, note="Adjusted down", modified_delta=3000.00
    )

    assert proposal.status == "modified_and_accepted"
    assert float(proposal.modified_delta_per_period) == 3000.00

    # Check forecast lines use modified delta
    result = await db_session.execute(
        select(ForecastLine).where(
            ForecastLine.version_id == new_version.id,
            ForecastLine.cost_center_id == proposal.cost_center_id,
            ForecastLine.category == "salary",
        )
    )
    for line in result.scalars().all():
        assert float(line.amount) == 53000.00  # 50000 + 3000


async def test_accept_creates_audit_entry(db_session: AsyncSession) -> None:
    """Accept creates an audit trail entry."""
    proposal, _ = await _create_test_proposal(db_session)

    await accept_proposal(db_session, proposal, note="Approved")

    result = await db_session.execute(
        select(ProposalDecisionAudit)
        .where(ProposalDecisionAudit.proposal_id == proposal.id)
    )
    audit = result.scalar_one()
    assert audit.from_status == "pending"
    assert audit.to_status == "accepted"
    assert audit.note == "Approved"


async def test_modify_audit_captures_delta_change(db_session: AsyncSession) -> None:
    """Modify-and-accept audit captures the difference between original and modified delta."""
    proposal, _ = await _create_test_proposal(db_session)

    await accept_proposal(db_session, proposal, modified_delta=3000.00)

    result = await db_session.execute(
        select(ProposalDecisionAudit)
        .where(ProposalDecisionAudit.proposal_id == proposal.id)
    )
    audit = result.scalar_one()
    assert audit.to_status == "modified_and_accepted"
    # delta_change = modified (3000) - original (5000) = -2000
    assert float(audit.delta_change) == -2000.00
