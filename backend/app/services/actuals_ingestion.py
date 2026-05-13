"""Actuals ingestion service — processes simulator output into queryable form.

In production this would process payroll files; here it wraps the monthly
simulator and provides query access to actual expense data.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.actual import Actual
from app.models.cost_center import CostCenter
from app.models.employee import Employee


async def get_actuals_by_period(
    session: AsyncSession,
    period: str,
    cost_center_id: int | None = None,
) -> list[dict[str, str | float | int]]:
    """Get aggregated actuals for a period, grouped by cost center and category."""
    query = (
        select(
            CostCenter.id.label("cost_center_id"),
            CostCenter.name.label("cost_center_name"),
            Actual.category,
            func.sum(Actual.amount).label("total_amount"),
            func.count(func.distinct(Actual.employee_id)).label("headcount"),
        )
        .join(Employee, Actual.employee_id == Employee.id)
        .join(CostCenter, Employee.cost_center_id == CostCenter.id)
        .where(Actual.period == period)
        .group_by(CostCenter.id, CostCenter.name, Actual.category)
        .order_by(CostCenter.id)
    )

    if cost_center_id is not None:
        query = query.where(CostCenter.id == cost_center_id)

    result = await session.execute(query)
    return [
        {
            "cost_center_id": row.cost_center_id,
            "cost_center_name": row.cost_center_name,
            "category": row.category,
            "total_amount": float(row.total_amount),
            "headcount": row.headcount,
        }
        for row in result.all()
    ]
