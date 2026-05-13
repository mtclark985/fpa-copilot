"""Pydantic schemas for forecast API responses."""

from typing import Optional

from pydantic import BaseModel


class ForecastLineSchema(BaseModel):
    """Single forecast line item."""

    id: int
    version_id: int
    cost_center_id: int
    cost_center_name: str
    period: str
    category: str
    amount: float
    headcount_eop: int

    model_config = {"from_attributes": True}


class ForecastVersionSchema(BaseModel):
    """Forecast version metadata."""

    id: int
    name: str
    is_active: bool
    source: Optional[str] = None
    created_at: Optional[str] = None
    parent_version_id: Optional[int] = None

    model_config = {"from_attributes": True}
