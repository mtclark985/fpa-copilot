"""Variance calculator — forecast vs actual with volume/rate decomposition.

Calculates variance at the cost_center x period x category level,
decomposing into volume variance (headcount delta) and rate variance
(cost per head delta). Assigns a materiality score (0-100).
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.actual import Actual
from app.models.cost_center import CostCenter
from app.models.employee import Employee
from app.models.forecast import ForecastLine, ForecastVersion
from app.models.variance import Variance


async def calculate_variances(
    session: AsyncSession,
    period: str,
) -> list[Variance]:
    """Calculate variances for a given period against the active forecast.

    Decomposes each variance into volume (headcount) and rate (cost per head)
    components. Volume variance = (actual HC - forecast HC) x forecast rate.
    Rate variance = actual HC x (actual rate - forecast rate).
    """
    # Get active forecast version
    fv_result = await session.execute(
        select(ForecastVersion)
        .where(ForecastVersion.is_active.is_(True))
        .order_by(ForecastVersion.id.desc())
        .limit(1)
    )
    forecast_version = fv_result.scalar_one_or_none()
    if forecast_version is None:
        return []

    # Get forecast lines for this period
    fl_result = await session.execute(
        select(ForecastLine).where(
            ForecastLine.version_id == forecast_version.id,
            ForecastLine.period == period,
        )
    )
    forecast_lines = list(fl_result.scalars().all())

    # Build forecast lookup: (cc_id, category) -> (amount, headcount)
    forecast_lookup: dict[tuple[int, str], tuple[float, int]] = {}
    for fl in forecast_lines:
        key = (fl.cost_center_id, fl.category)
        forecast_lookup[key] = (float(fl.amount), fl.headcount_eop)

    # Get actual totals grouped by cost center and category
    actual_query = (
        select(
            Employee.cost_center_id,
            Actual.category,
            func.sum(Actual.amount).label("total_amount"),
            func.count(func.distinct(Actual.employee_id)).label("headcount"),
        )
        .join(Employee, Actual.employee_id == Employee.id)
        .where(Actual.period == period)
        .group_by(Employee.cost_center_id, Actual.category)
    )
    actual_result = await session.execute(actual_query)
    actual_rows = actual_result.all()

    # Build actual lookup: (cc_id, category) -> (amount, headcount)
    actual_lookup: dict[tuple[int, str], tuple[float, int]] = {}
    for row in actual_rows:
        key = (row.cost_center_id, row.category)
        actual_lookup[key] = (float(row.total_amount), row.headcount)

    # Calculate variances for all keys present in either forecast or actuals
    all_keys = set(forecast_lookup.keys()) | set(actual_lookup.keys())
    variances: list[Variance] = []

    # Collect all variances to compute stats for materiality scoring
    raw_variances: list[tuple[tuple[int, str], float, float, float, float, int, int]] = []

    for key in all_keys:
        cc_id, category = key
        forecast_amount, forecast_hc = forecast_lookup.get(key, (0.0, 0))
        actual_amount, actual_hc = actual_lookup.get(key, (0.0, 0))

        variance_amount = actual_amount - forecast_amount

        # Avoid division by zero for variance percentage
        if forecast_amount != 0:
            variance_pct = (variance_amount / forecast_amount) * 100
        else:
            variance_pct = 100.0 if actual_amount > 0 else 0.0

        # Volume/rate decomposition
        # Volume variance = (actual HC - forecast HC) x forecast rate per head
        # Rate variance = actual HC x (actual rate - forecast rate)
        forecast_rate = forecast_amount / forecast_hc if forecast_hc > 0 else 0
        actual_rate = actual_amount / actual_hc if actual_hc > 0 else 0

        volume_variance = (actual_hc - forecast_hc) * forecast_rate
        rate_variance = actual_hc * (actual_rate - forecast_rate)

        raw_variances.append((
            key, forecast_amount, actual_amount, variance_amount,
            variance_pct, forecast_hc, actual_hc,
        ))

    # Calculate materiality scores
    # Materiality = weighted combination of absolute $, % variance, and relative size
    abs_amounts = [abs(rv[3]) for rv in raw_variances]
    max_abs = max(abs_amounts) if abs_amounts else 1.0
    abs_pcts = [abs(rv[4]) for rv in raw_variances]
    max_pct = max(abs_pcts) if abs_pcts else 1.0

    for rv in raw_variances:
        key, forecast_amount, actual_amount, variance_amount, variance_pct, forecast_hc, actual_hc = rv
        cc_id, category = key

        forecast_rate = forecast_amount / forecast_hc if forecast_hc > 0 else 0
        actual_rate = actual_amount / actual_hc if actual_hc > 0 else 0
        volume_variance = (actual_hc - forecast_hc) * forecast_rate
        rate_variance = actual_hc * (actual_rate - forecast_rate)

        # Materiality score: 0-100
        dollar_score = (abs(variance_amount) / max_abs * 40) if max_abs > 0 else 0
        pct_score = (abs(variance_pct) / max_pct * 30) if max_pct > 0 else 0
        # Unexpectedness bonus: larger % variances get extra weight
        unexpected_score = min(30, abs(variance_pct) * 2)
        materiality = min(100, dollar_score + pct_score + unexpected_score)

        var = Variance(
            forecast_version_id=forecast_version.id,
            cost_center_id=cc_id,
            period=period,
            category=category,
            forecast_amount=round(forecast_amount, 2),
            actual_amount=round(actual_amount, 2),
            variance_amount=round(variance_amount, 2),
            variance_pct=round(variance_pct, 4),
            volume_variance=round(volume_variance, 2),
            rate_variance=round(rate_variance, 2),
            materiality_score=round(materiality, 1),
        )
        session.add(var)
        variances.append(var)

    await session.flush()
    await session.commit()

    return variances
