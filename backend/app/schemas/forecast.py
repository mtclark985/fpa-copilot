"""Pydantic schemas for forecast API responses."""

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

    model_config = {"from_attributes": True}
