"""Pydantic schemas for proposal API responses."""

from typing import Any, Optional

from pydantic import BaseModel


class ProposalSchema(BaseModel):
    """Proposal summary for list views."""

    id: int
    created_at: str
    created_for_period: str
    status: str
    cost_center_id: int
    cost_center_name: str
    category: str
    affected_periods: list[str]
    delta_per_period: float
    agent_rationale: str
    driving_variance_ids: list[int]
    attributed_events: list[Any]
    confidence: str
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    decision_note: Optional[str] = None
    modified_delta_per_period: Optional[float] = None
    resulting_forecast_version_id: Optional[int] = None


class ProposalDetailSchema(ProposalSchema):
    """Full proposal detail including driving variances and attributions."""

    driving_variances: list[Any] = []
    attribution_records: list[Any] = []


class DecisionRequest(BaseModel):
    """Request body for accept/reject actions."""
    note: Optional[str] = None


class ModifyAndAcceptRequest(BaseModel):
    """Request body for modify-and-accept action."""
    modified_delta_per_period: float
    note: Optional[str] = None
