"""Dashboard KPI endpoint — aggregated metrics for the overview page."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.actual import Actual
from app.models.employee import Employee
from app.models.forecast import ForecastLine, ForecastVersion
from app.models.variance import Variance

router = APIRouter()


@router.get("/kpis/dashboard")
async def get_dashboard_kpis(
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    """Aggregated KPIs for the dashboard page."""
    # Current month (latest period with actuals)
    latest_period_result = await session.execute(select(func.max(Actual.period)))
    current_month = latest_period_result.scalar() or "2026-01"

    # Headcount EOP (active employees)
    hc_result = await session.execute(
        select(func.count()).select_from(Employee).where(
            Employee.termination_date.is_(None)
        )
    )
    headcount_eop = hc_result.scalar() or 0

    # YTD actual comp
    year = current_month[:4]
    ytd_actual_result = await session.execute(
        select(func.sum(Actual.amount)).where(
            Actual.period >= f"{year}-01",
            Actual.period <= current_month,
        )
    )
    ytd_actuals = float(ytd_actual_result.scalar() or 0)

    # YTD forecast
    fv_result = await session.execute(
        select(ForecastVersion)
        .where(ForecastVersion.is_active.is_(True))
        .order_by(ForecastVersion.id.desc())
        .limit(1)
    )
    fv = fv_result.scalar_one_or_none()

    ytd_forecast = 0.0
    fy_forecast = 0.0
    if fv:
        ytd_fc_result = await session.execute(
            select(func.sum(ForecastLine.amount)).where(
                ForecastLine.version_id == fv.id,
                ForecastLine.period >= f"{year}-01",
                ForecastLine.period <= current_month,
            )
        )
        ytd_forecast = float(ytd_fc_result.scalar() or 0)

        fy_fc_result = await session.execute(
            select(func.sum(ForecastLine.amount)).where(
                ForecastLine.version_id == fv.id,
                ForecastLine.period >= f"{year}-01",
                ForecastLine.period <= f"{year}-12",
            )
        )
        fy_forecast = float(fy_fc_result.scalar() or 0)

    ytd_variance = ytd_actuals - ytd_forecast

    # Monthly actual vs forecast for chart
    monthly_data = []
    periods_result = await session.execute(
        select(Actual.period).distinct().order_by(Actual.period)
    )
    periods = [row[0] for row in periods_result.all()]

    for period in periods:
        act_result = await session.execute(
            select(func.sum(Actual.amount)).where(Actual.period == period)
        )
        actual_total = float(act_result.scalar() or 0)

        fc_total = 0.0
        if fv:
            fc_result = await session.execute(
                select(func.sum(ForecastLine.amount)).where(
                    ForecastLine.version_id == fv.id,
                    ForecastLine.period == period,
                )
            )
            fc_total = float(fc_result.scalar() or 0)

        monthly_data.append({
            "period": period,
            "actual": round(actual_total, 2),
            "forecast": round(fc_total, 2),
        })

    # Recent agent activity
    agent_result = await session.execute(
        select(Variance)
        .where(Variance.agent_severity.isnot(None))
        .order_by(Variance.detected_at.desc())
        .limit(10)
    )
    recent_assessments = [
        {
            "id": v.id,
            "period": v.period,
            "cost_center_id": v.cost_center_id,
            "category": v.category,
            "severity": v.agent_severity,
            "rationale": v.agent_rationale,
            "suggested_action": v.agent_suggested_action,
        }
        for v in agent_result.scalars().all()
    ]

    return {
        "current_month": current_month,
        "headcount_eop": headcount_eop,
        "ytd_actuals": round(ytd_actuals, 2),
        "ytd_variance": round(ytd_variance, 2),
        "fy_forecast": round(fy_forecast, 2),
        "monthly_data": monthly_data,
        "recent_assessments": recent_assessments,
    }
