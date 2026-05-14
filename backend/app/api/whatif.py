"""What-If scenario API — stateless scenario calculation.

Runs forecast computation with adjusted assumptions and returns
the result alongside a delta comparison to the active forecast.
No data is persisted.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.forecast import ForecastLine, ForecastVersion
from app.services.forecast_assumptions import DEFAULT_ASSUMPTIONS, ForecastAssumptions
from app.services.forecast_engine import compute_forecast

router = APIRouter(prefix="/what-if", tags=["what-if"])


class WhatIfScenario(BaseModel):
    """Input dials for a what-if scenario."""

    attrition_rate: float = Field(
        default=DEFAULT_ASSUMPTIONS.annual_attrition_rate,
        ge=0.05, le=0.25,
        description="Annual attrition rate (0.05 to 0.25)",
    )
    merit_pct: float = Field(
        default=DEFAULT_ASSUMPTIONS.merit_avg_pct,
        ge=0.0, le=0.10,
        description="Merit increase percentage (0.0 to 0.10)",
    )
    benefits_load_pct: float = Field(
        default=DEFAULT_ASSUMPTIONS.benefits_load_pct,
        ge=0.10, le=0.25,
        description="Benefits load as % of salary (0.10 to 0.25)",
    )
    hire_pace_per_quarter: float = Field(
        default=DEFAULT_ASSUMPTIONS.quarterly_hire_growth,
        ge=0.0, le=0.05,
        description="Quarterly hire growth rate (0.0 to 0.05)",
    )
    headcount_acceleration_multiplier: float = Field(
        default=1.0,
        ge=0.5, le=1.5,
        description="Multiplier for all forward hires (0.5 = freeze, 1.5 = 50% faster)",
    )


class ForecastLineOutput(BaseModel):
    """A single forecast line in the response."""

    period: str
    category: str
    amount: float


class DeltaSummary(BaseModel):
    """Summary of the difference between scenario and baseline."""

    total_18_month: float
    fy_landing: float
    by_category: dict[str, float]


class WhatIfResponse(BaseModel):
    """Response from the what-if endpoint."""

    scenario_lines: list[ForecastLineOutput]
    baseline_lines: list[ForecastLineOutput]
    delta: DeltaSummary


@router.post("/run", response_model=WhatIfResponse)
async def run_what_if(
    scenario: WhatIfScenario,
    session: AsyncSession = Depends(get_session),
) -> WhatIfResponse:
    """Run a what-if scenario calculation.

    Computes a forecast with the given assumptions, compares it to the
    active forecast, and returns both along with delta analysis.
    This is stateless — nothing is written to the database.
    """
    # Build scenario assumptions from dials
    scenario_assumptions = ForecastAssumptions(
        annual_attrition_rate=scenario.attrition_rate,
        merit_avg_pct=scenario.merit_pct,
        benefits_load_pct=scenario.benefits_load_pct,
        quarterly_hire_growth=scenario.hire_pace_per_quarter,
    )

    # Compute scenario forecast
    scenario_data = await compute_forecast(
        session,
        assumptions=scenario_assumptions,
        headcount_acceleration=scenario.headcount_acceleration_multiplier,
    )

    # Aggregate scenario lines by period × category
    scenario_by_pc: dict[tuple[str, str], float] = {}
    for line in scenario_data:
        key = (line.period, line.category)
        scenario_by_pc[key] = scenario_by_pc.get(key, 0) + line.amount

    scenario_lines = [
        ForecastLineOutput(period=period, category=cat, amount=round(amount, 2))
        for (period, cat), amount in sorted(scenario_by_pc.items())
    ]

    # Get active forecast baseline
    fv_result = await session.execute(
        select(ForecastVersion)
        .where(ForecastVersion.is_active.is_(True))
        .order_by(ForecastVersion.id.desc())
        .limit(1)
    )
    fv = fv_result.scalar_one_or_none()

    baseline_by_pc: dict[tuple[str, str], float] = {}
    if fv:
        fl_result = await session.execute(
            select(
                ForecastLine.period,
                ForecastLine.category,
                func.sum(ForecastLine.amount),
            )
            .where(ForecastLine.version_id == fv.id)
            .group_by(ForecastLine.period, ForecastLine.category)
            .order_by(ForecastLine.period, ForecastLine.category)
        )
        for period, category, total in fl_result.all():
            baseline_by_pc[(period, category)] = float(total)

    baseline_lines = [
        ForecastLineOutput(period=period, category=cat, amount=round(amount, 2))
        for (period, cat), amount in sorted(baseline_by_pc.items())
    ]

    # Compute deltas
    all_keys = set(scenario_by_pc.keys()) | set(baseline_by_pc.keys())

    total_delta = 0.0
    fy_delta = 0.0
    cat_delta: dict[str, float] = {}

    for key in all_keys:
        s = scenario_by_pc.get(key, 0)
        b = baseline_by_pc.get(key, 0)
        diff = s - b
        total_delta += diff

        period, category = key
        cat_delta[category] = cat_delta.get(category, 0) + diff

        # FY landing = same calendar year as start
        if period.startswith("2026-"):
            fy_delta += diff

    delta = DeltaSummary(
        total_18_month=round(total_delta, 2),
        fy_landing=round(fy_delta, 2),
        by_category={k: round(v, 2) for k, v in sorted(cat_delta.items())},
    )

    return WhatIfResponse(
        scenario_lines=scenario_lines,
        baseline_lines=baseline_lines,
        delta=delta,
    )
