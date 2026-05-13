"""Employee and cost center API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.cost_center import CostCenter
from app.models.employee import Employee

router = APIRouter()


@router.get("/employees")
async def get_employees(
    session: AsyncSession = Depends(get_session),
    cost_center_id: Optional[int] = Query(None),
) -> list[dict[str, object]]:
    """List employees, optionally filtered by cost center."""
    query = select(Employee, CostCenter.name).join(
        CostCenter, Employee.cost_center_id == CostCenter.id
    )
    if cost_center_id:
        query = query.where(Employee.cost_center_id == cost_center_id)

    query = query.order_by(Employee.employee_number).limit(100)
    result = await session.execute(query)

    return [
        {
            "id": emp.id,
            "employee_number": emp.employee_number,
            "name": emp.name,
            "hire_date": emp.hire_date.isoformat(),
            "termination_date": emp.termination_date.isoformat() if emp.termination_date else None,
            "cost_center_id": emp.cost_center_id,
            "cost_center_name": cc_name,
            "job_level": emp.job_level,
            "base_salary": float(emp.base_salary),
            "bonus_target_pct": float(emp.bonus_target_pct),
            "location": emp.location,
        }
        for emp, cc_name in result.all()
    ]


@router.get("/cost-centers")
async def get_cost_centers(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    """List all cost centers with hierarchy info."""
    result = await session.execute(
        select(CostCenter).order_by(CostCenter.code)
    )
    cost_centers = result.scalars().all()

    return [
        {
            "id": cc.id,
            "code": cc.code,
            "name": cc.name,
            "parent_id": cc.parent_id,
            "vp_owner": cc.vp_owner,
        }
        for cc in cost_centers
    ]
