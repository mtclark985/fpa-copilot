"""Forecast API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.cost_center import CostCenter
from app.models.forecast import ForecastLine, ForecastVersion
from app.schemas.forecast import ForecastLineSchema, ForecastVersionSchema

router = APIRouter()


@router.get("/forecast", response_model=list[ForecastLineSchema])
async def get_forecast(
    session: AsyncSession = Depends(get_session),
    period_start: Optional[str] = Query(None, description="Start period YYYY-MM"),
    period_end: Optional[str] = Query(None, description="End period YYYY-MM"),
    cost_center_id: Optional[int] = Query(None),
    version_id: Optional[int] = Query(None, description="Specific version ID; defaults to active"),
) -> list[ForecastLineSchema]:
    """Get forecast lines with optional filters."""
    if version_id:
        version = await session.get(ForecastVersion, version_id)
    else:
        version_result = await session.execute(
            select(ForecastVersion)
            .where(ForecastVersion.is_active.is_(True))
            .order_by(ForecastVersion.id.desc())
            .limit(1)
        )
        version = version_result.scalar_one_or_none()

    if version is None:
        return []

    query = select(ForecastLine, CostCenter.name).join(
        CostCenter, ForecastLine.cost_center_id == CostCenter.id
    ).where(ForecastLine.version_id == version.id)

    if period_start:
        query = query.where(ForecastLine.period >= period_start)
    if period_end:
        query = query.where(ForecastLine.period <= period_end)
    if cost_center_id:
        query = query.where(ForecastLine.cost_center_id == cost_center_id)

    query = query.order_by(ForecastLine.period, ForecastLine.cost_center_id)
    result = await session.execute(query)

    return [
        ForecastLineSchema(
            id=line.id,
            version_id=line.version_id,
            cost_center_id=line.cost_center_id,
            cost_center_name=cc_name,
            period=line.period,
            category=line.category,
            amount=float(line.amount),
            headcount_eop=line.headcount_eop,
        )
        for line, cc_name in result.all()
    ]


@router.get("/forecast/versions", response_model=list[ForecastVersionSchema])
async def list_forecast_versions(
    session: AsyncSession = Depends(get_session),
) -> list[ForecastVersionSchema]:
    """List all forecast versions, newest first."""
    result = await session.execute(
        select(ForecastVersion).order_by(ForecastVersion.id.desc())
    )
    versions = result.scalars().all()
    return [
        ForecastVersionSchema(
            id=v.id,
            name=v.name,
            is_active=v.is_active,
            source=getattr(v, "source", None) or "initial_plan",
            created_at=v.created_at.isoformat() if v.created_at else "",
            parent_version_id=v.parent_version_id,
        )
        for v in versions
    ]
