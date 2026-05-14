"""Transparency API — read-only endpoints for the Data & Assumptions page.

Exposes employees, hiring plan, forecast assumptions, and simulator events
so users can inspect the data underlying the forecast.
"""

import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.cost_center import CostCenter
from app.models.employee import Employee
from app.models.position import Position
from app.seed.monthly_simulator import STORY_VARIANCES
from app.services.forecast_assumptions import ASSUMPTIONS_METADATA

router = APIRouter(prefix="/transparency", tags=["transparency"])


@router.get("/employees")
async def get_transparency_employees(
    session: AsyncSession = Depends(get_session),
    search: Optional[str] = Query(None, description="Filter by name or employee_number"),
    cost_center_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None, description="active, terminated, or all"),
    sort_by: Optional[str] = Query("employee_number", description="Column to sort by"),
    sort_dir: Optional[str] = Query("asc", description="asc or desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
) -> dict[str, object]:
    """Paginated, filterable, sortable employee list."""
    query = (
        select(Employee, CostCenter.name, CostCenter.code)
        .join(CostCenter, Employee.cost_center_id == CostCenter.id)
    )

    # Search filter
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Employee.name.ilike(pattern),
                Employee.employee_number.ilike(pattern),
            )
        )

    # Cost center filter
    if cost_center_id:
        query = query.where(Employee.cost_center_id == cost_center_id)

    # Status filter
    if status == "active":
        query = query.where(Employee.termination_date.is_(None))
    elif status == "terminated":
        query = query.where(Employee.termination_date.isnot(None))

    # Count total before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Sorting
    sort_column = getattr(Employee, sort_by, Employee.employee_number)
    if sort_dir == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)

    employees = [
        {
            "id": emp.id,
            "employee_number": emp.employee_number,
            "name": emp.name,
            "cost_center_id": emp.cost_center_id,
            "cost_center_name": cc_name,
            "cost_center_code": cc_code,
            "job_level": emp.job_level,
            "location": emp.location,
            "hire_date": emp.hire_date.isoformat(),
            "base_salary": float(emp.base_salary),
            "bonus_target_pct": float(emp.bonus_target_pct),
            "status": "terminated" if emp.termination_date else "active",
            "termination_date": emp.termination_date.isoformat() if emp.termination_date else None,
        }
        for emp, cc_name, cc_code in result.all()
    ]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "employees": employees,
    }


@router.get("/hiring-plan")
async def get_hiring_plan(
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    """Open positions and recent hires."""
    # Open positions
    pos_result = await session.execute(
        select(Position, CostCenter.name, CostCenter.code)
        .join(CostCenter, Position.cost_center_id == CostCenter.id)
        .where(Position.status == "open")
        .order_by(Position.target_start_date)
    )

    open_positions = [
        {
            "id": pos.id,
            "cost_center_id": pos.cost_center_id,
            "cost_center_name": cc_name,
            "cost_center_code": cc_code,
            "job_level": pos.job_level,
            "target_start_date": pos.target_start_date.isoformat(),
            "status": pos.status,
        }
        for pos, cc_name, cc_code in pos_result.all()
    ]

    # Recent hires (last 6 months)
    six_months_ago = datetime.date.today() - datetime.timedelta(days=180)
    hires_result = await session.execute(
        select(Employee, CostCenter.name, CostCenter.code)
        .join(CostCenter, Employee.cost_center_id == CostCenter.id)
        .where(Employee.hire_date >= six_months_ago)
        .order_by(Employee.hire_date.desc())
    )

    recent_hires = [
        {
            "id": emp.id,
            "employee_number": emp.employee_number,
            "name": emp.name,
            "cost_center_name": cc_name,
            "cost_center_code": cc_code,
            "job_level": emp.job_level,
            "hire_date": emp.hire_date.isoformat(),
            "base_salary": float(emp.base_salary),
            "location": emp.location,
            "source": "planned" if emp.employee_number.startswith("E0") else "unplanned",
        }
        for emp, cc_name, cc_code in hires_result.all()
    ]

    return {
        "open_positions": open_positions,
        "recent_hires": recent_hires,
    }


@router.get("/assumptions")
async def get_assumptions() -> list[dict[str, object]]:
    """Current forecast assumptions with metadata."""
    return ASSUMPTIONS_METADATA


@router.get("/simulator-events")
async def get_simulator_events() -> list[dict[str, object]]:
    """Chronological list of story variances injected by the simulator."""
    events = []
    for period in sorted(STORY_VARIANCES.keys()):
        data = STORY_VARIANCES[period]
        event_type = _classify_event(data)
        events.append({
            "period": period,
            "event_type": event_type,
            "narrative": str(data.get("story", "")),
            "details": {
                k: v for k, v in data.items()
                if k not in ("story", "cc_code_prefix")
            },
            "affected_area": str(data.get("cc_code_prefix", "")),
        })
    return events


def _classify_event(data: dict) -> str:
    """Classify a story variance into an event type."""
    if "extra_hires" in data and "extra_departures" in data:
        return "reorganization"
    if "extra_hires" in data:
        if data.get("salary_premium_pct"):
            return "premium_hire"
        return "unplanned_hire_cluster"
    if "extra_departures" in data:
        return "unplanned_departures"
    if "cola_pct" in data:
        return "cola_adjustment"
    if "retention_bonuses" in data:
        return "retention_bonus_event"
    if "spot_bonuses" in data:
        return "spot_bonus_event"
    if "overtime_pct" in data:
        return "overtime_event"
    return "other"
