"""Pydantic schemas for variance API responses."""

from typing import Optional

from pydantic import BaseModel


class VarianceSchema(BaseModel):
    """Variance summary for list views."""

    id: int
    cost_center_id: int
    cost_center_name: str
    period: str
    category: str
    forecast_amount: float
    actual_amount: float
    variance_amount: float
    variance_pct: float
    volume_variance: float
    rate_variance: float
    materiality_score: float
    agent_severity: Optional[str] = None
    agent_unexpectedness: Optional[str] = None
    agent_rationale: Optional[str] = None
    agent_suggested_action: Optional[str] = None

    model_config = {"from_attributes": True}
