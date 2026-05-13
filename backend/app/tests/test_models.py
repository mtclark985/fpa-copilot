"""Test that ORM models can be created, persisted, and queried.

Uses unique codes/numbers with TEST- prefix to avoid conflicts with seed data.
"""

import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Actual,
    AttributionRecord,
    CostCenter,
    Employee,
    ForecastLine,
    ForecastVersion,
    ForecastProposal,
    Position,
    ProposalDecisionAudit,
    Variance,
)


def _uid() -> str:
    return uuid.uuid4().hex[:8]


async def test_cost_center_crud(db_session: AsyncSession) -> None:
    """Cost center can be created and queried."""
    code = f"TEST-{_uid()}"
    cc = CostCenter(code=code, name="Test CC", vp_owner="Jane Smith")
    db_session.add(cc)
    await db_session.flush()

    result = await db_session.execute(select(CostCenter).where(CostCenter.code == code))
    fetched = result.scalar_one()
    assert fetched.name == "Test CC"


async def test_employee_with_cost_center(db_session: AsyncSession) -> None:
    """Employee links to its cost center via FK."""
    cc = CostCenter(code=f"TEST-{_uid()}", name="Finance", vp_owner="Bob Jones")
    db_session.add(cc)
    await db_session.flush()

    emp = Employee(
        employee_number=f"T{_uid()}",
        name="Alice Analyst",
        hire_date=datetime.date(2023, 6, 15),
        cost_center_id=cc.id,
        job_level="L4",
        base_salary=95000.00,
        bonus_target_pct=10.0,
        location="Charlotte",
    )
    db_session.add(emp)
    await db_session.flush()

    result = await db_session.execute(select(Employee).where(Employee.id == emp.id))
    fetched = result.scalar_one()
    assert fetched.cost_center_id == cc.id
    assert float(fetched.base_salary) == 95000.00


async def test_position_model(db_session: AsyncSession) -> None:
    """Position can be created with open status."""
    cc = CostCenter(code=f"TEST-{_uid()}", name="Marketing", vp_owner="Carol Lee")
    db_session.add(cc)
    await db_session.flush()

    pos = Position(
        cost_center_id=cc.id,
        job_level="L5",
        status="open",
        target_start_date=datetime.date(2026, 3, 1),
    )
    db_session.add(pos)
    await db_session.flush()

    result = await db_session.execute(select(Position).where(Position.id == pos.id))
    fetched = result.scalar_one()
    assert fetched.job_level == "L5"
    assert fetched.status == "open"


async def test_forecast_version_and_lines(db_session: AsyncSession) -> None:
    """Forecast version with lines can be created and queried."""
    cc = CostCenter(code=f"TEST-{_uid()}", name="HR", vp_owner="Dan White")
    db_session.add(cc)
    await db_session.flush()

    fv = ForecastVersion(name=f"Test Plan {_uid()}", is_active=False)
    db_session.add(fv)
    await db_session.flush()

    line = ForecastLine(
        version_id=fv.id,
        cost_center_id=cc.id,
        period="2099-01",
        category="salary",
        amount=500000.00,
        headcount_eop=50,
    )
    db_session.add(line)
    await db_session.flush()

    result = await db_session.execute(
        select(ForecastLine).where(ForecastLine.version_id == fv.id)
    )
    fetched = result.scalar_one()
    assert fetched.period == "2099-01"
    assert float(fetched.amount) == 500000.00


async def test_actual_model(db_session: AsyncSession) -> None:
    """Actual expense can be linked to an employee."""
    cc = CostCenter(code=f"TEST-{_uid()}", name="Operations", vp_owner="Eve Black")
    db_session.add(cc)
    await db_session.flush()

    emp = Employee(
        employee_number=f"T{_uid()}",
        name="Test Worker",
        hire_date=datetime.date(2024, 1, 1),
        cost_center_id=cc.id,
        job_level="L3",
        base_salary=75000.00,
        bonus_target_pct=8.0,
        location="Remote",
    )
    db_session.add(emp)
    await db_session.flush()

    actual = Actual(
        employee_id=emp.id,
        period="2099-01",
        category="salary",
        amount=6250.00,
    )
    db_session.add(actual)
    await db_session.flush()

    result = await db_session.execute(select(Actual).where(Actual.employee_id == emp.id))
    fetched = result.scalar_one()
    assert float(fetched.amount) == 6250.00


async def test_variance_model(db_session: AsyncSession) -> None:
    """Variance record stores both calculated and agent fields."""
    cc = CostCenter(code=f"TEST-{_uid()}", name="Sales", vp_owner="Frank Green")
    db_session.add(cc)
    await db_session.flush()

    fv = ForecastVersion(name=f"Test Plan {_uid()}", is_active=False)
    db_session.add(fv)
    await db_session.flush()

    var = Variance(
        forecast_version_id=fv.id,
        cost_center_id=cc.id,
        period="2099-01",
        category="salary",
        forecast_amount=100000.00,
        actual_amount=105000.00,
        variance_amount=5000.00,
        variance_pct=5.0,
        volume_variance=3000.00,
        rate_variance=2000.00,
        materiality_score=65.0,
        agent_severity="medium",
        agent_rationale="Unplanned hire",
    )
    db_session.add(var)
    await db_session.flush()

    result = await db_session.execute(select(Variance).where(Variance.id == var.id))
    fetched = result.scalar_one()
    assert fetched.agent_severity == "medium"
    assert float(fetched.variance_amount) == 5000.00


async def test_attribution_record(db_session: AsyncSession) -> None:
    """Attribution record links to a variance with structured drivers."""
    cc = CostCenter(code=f"TEST-{_uid()}", name="Risk", vp_owner="Gail Adams")
    db_session.add(cc)
    await db_session.flush()

    fv = ForecastVersion(name=f"Test Plan {_uid()}", is_active=False)
    db_session.add(fv)
    await db_session.flush()

    var = Variance(
        forecast_version_id=fv.id,
        cost_center_id=cc.id,
        period="2099-02",
        category="salary",
        forecast_amount=80000.00,
        actual_amount=90000.00,
        variance_amount=10000.00,
        variance_pct=12.5,
    )
    db_session.add(var)
    await db_session.flush()

    attr = AttributionRecord(
        variance_id=var.id,
        attribution_type="early_hire",
        narrative="Risk team filled position REQ-1041 in January, 60 days ahead of plan.",
        structured_drivers=[
            {"type": "hire", "employee_id": 412, "expected_start": "2026-03-01", "actual_start": "2026-01-15"}
        ],
        confidence="high",
    )
    db_session.add(attr)
    await db_session.flush()

    result = await db_session.execute(
        select(AttributionRecord).where(AttributionRecord.variance_id == var.id)
    )
    fetched = result.scalar_one()
    assert fetched.attribution_type == "early_hire"
    assert fetched.confidence == "high"
    assert len(fetched.structured_drivers) == 1


async def test_forecast_proposal(db_session: AsyncSession) -> None:
    """Forecast proposal can be created with pending status and JSON fields."""
    cc = CostCenter(code=f"TEST-{_uid()}", name="Engineering", vp_owner="Hank Brown")
    db_session.add(cc)
    await db_session.flush()

    proposal = ForecastProposal(
        created_for_period="2026-06",
        status="pending",
        cost_center_id=cc.id,
        category="salary",
        affected_periods=["2026-07", "2026-08", "2026-09"],
        delta_per_period=5000.00,
        agent_rationale="Early hires in Risk require salary run-rate increase.",
        driving_variance_ids=[1, 2],
        attributed_events=[{"type": "early_hire", "employee_id": 412}],
        confidence="high",
    )
    db_session.add(proposal)
    await db_session.flush()

    result = await db_session.execute(
        select(ForecastProposal).where(ForecastProposal.id == proposal.id)
    )
    fetched = result.scalar_one()
    assert fetched.status == "pending"
    assert len(fetched.affected_periods) == 3
    assert float(fetched.delta_per_period) == 5000.00


async def test_proposal_decision_audit(db_session: AsyncSession) -> None:
    """Audit trail records proposal state transitions."""
    cc = CostCenter(code=f"TEST-{_uid()}", name="Data", vp_owner="Iris Chen")
    db_session.add(cc)
    await db_session.flush()

    proposal = ForecastProposal(
        created_for_period="2026-06",
        status="pending",
        cost_center_id=cc.id,
        category="salary",
        affected_periods=["2026-07"],
        delta_per_period=3000.00,
        agent_rationale="Test rationale",
        driving_variance_ids=[],
        attributed_events=[],
        confidence="medium",
    )
    db_session.add(proposal)
    await db_session.flush()

    audit = ProposalDecisionAudit(
        proposal_id=proposal.id,
        from_status="pending",
        to_status="accepted",
        note="Looks good",
    )
    db_session.add(audit)
    await db_session.flush()

    result = await db_session.execute(
        select(ProposalDecisionAudit).where(ProposalDecisionAudit.proposal_id == proposal.id)
    )
    fetched = result.scalar_one()
    assert fetched.from_status == "pending"
    assert fetched.to_status == "accepted"


async def test_forecast_version_parent_and_source(db_session: AsyncSession) -> None:
    """ForecastVersion supports parent_version_id and source columns."""
    parent = ForecastVersion(name=f"Parent {_uid()}", is_active=False, source="initial_plan")
    db_session.add(parent)
    await db_session.flush()

    child = ForecastVersion(
        name=f"Child {_uid()}",
        is_active=False,
        parent_version_id=parent.id,
        source="proposal_accepted",
    )
    db_session.add(child)
    await db_session.flush()

    result = await db_session.execute(
        select(ForecastVersion).where(ForecastVersion.id == child.id)
    )
    fetched = result.scalar_one()
    assert fetched.parent_version_id == parent.id
    assert fetched.source == "proposal_accepted"
