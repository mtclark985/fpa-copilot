"""Actuals API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.services.actuals_ingestion import get_actuals_by_period

router = APIRouter()


@router.get("/actuals")
async def get_actuals(
    session: AsyncSession = Depends(get_session),
    period: Optional[str] = Query(None, description="Period YYYY-MM"),
    cost_center_id: Optional[int] = Query(None),
) -> list[dict[str, str | float | int]]:
    """Get aggregated actuals by cost center and category."""
    if period is None:
        return []
    return await get_actuals_by_period(session, period, cost_center_id)
