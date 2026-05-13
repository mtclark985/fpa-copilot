"""Variance API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.cost_center import CostCenter
from app.models.variance import Variance
from app.schemas.variance import VarianceSchema
from app.services.variance_calculator import calculate_variances

router = APIRouter()


@router.get("/variances", response_model=list[VarianceSchema])
async def get_variances(
    session: AsyncSession = Depends(get_session),
    period: Optional[str] = Query(None),
    cost_center_id: Optional[int] = Query(None),
    min_materiality: Optional[float] = Query(None),
) -> list[VarianceSchema]:
    """Get variances with optional filters."""
    query = select(Variance, CostCenter.name).join(
        CostCenter, Variance.cost_center_id == CostCenter.id
    )

    if period:
        query = query.where(Variance.period == period)
    if cost_center_id:
        query = query.where(Variance.cost_center_id == cost_center_id)
    if min_materiality is not None:
        query = query.where(Variance.materiality_score >= min_materiality)

    query = query.order_by(Variance.materiality_score.desc())
    result = await session.execute(query)

    return [
        VarianceSchema(
            id=var.id,
            cost_center_id=var.cost_center_id,
            cost_center_name=cc_name,
            period=var.period,
            category=var.category,
            forecast_amount=float(var.forecast_amount),
            actual_amount=float(var.actual_amount),
            variance_amount=float(var.variance_amount),
            variance_pct=float(var.variance_pct),
            volume_variance=float(var.volume_variance),
            rate_variance=float(var.rate_variance),
            materiality_score=float(var.materiality_score),
            agent_severity=var.agent_severity,
            agent_unexpectedness=var.agent_unexpectedness,
            agent_rationale=var.agent_rationale,
            agent_suggested_action=var.agent_suggested_action,
        )
        for var, cc_name in result.all()
    ]


@router.get("/variances/{variance_id}", response_model=VarianceSchema)
async def get_variance_detail(
    variance_id: int,
    session: AsyncSession = Depends(get_session),
) -> VarianceSchema:
    """Get a single variance with full details."""
    result = await session.execute(
        select(Variance, CostCenter.name)
        .join(CostCenter, Variance.cost_center_id == CostCenter.id)
        .where(Variance.id == variance_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Variance not found")

    var, cc_name = row
    return VarianceSchema(
        id=var.id,
        cost_center_id=var.cost_center_id,
        cost_center_name=cc_name,
        period=var.period,
        category=var.category,
        forecast_amount=float(var.forecast_amount),
        actual_amount=float(var.actual_amount),
        variance_amount=float(var.variance_amount),
        variance_pct=float(var.variance_pct),
        volume_variance=float(var.volume_variance),
        rate_variance=float(var.rate_variance),
        materiality_score=float(var.materiality_score),
        agent_severity=var.agent_severity,
        agent_unexpectedness=var.agent_unexpectedness,
        agent_rationale=var.agent_rationale,
        agent_suggested_action=var.agent_suggested_action,
    )


@router.post("/variances/{period}/calculate")
async def trigger_variance_calculation(
    period: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str | int]:
    """Calculate variances for a specific period."""
    variances = await calculate_variances(session, period)
    return {"period": period, "variances_calculated": len(variances)}
