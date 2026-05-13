"""Employee model — individual headcount record."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.actual import Actual
    from app.models.cost_center import CostCenter


class Employee(Base):
    """Represents a single employee with comp and org details."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    hire_date: Mapped[datetime.date]
    termination_date: Mapped[Optional[datetime.date]] = mapped_column(nullable=True)
    cost_center_id: Mapped[int] = mapped_column(ForeignKey("cost_centers.id"), index=True)
    job_level: Mapped[str] = mapped_column(String(10))
    base_salary: Mapped[float] = mapped_column(Numeric(12, 2))
    bonus_target_pct: Mapped[float] = mapped_column(Numeric(5, 2))
    location: Mapped[str] = mapped_column(String(50))

    cost_center: Mapped["CostCenter"] = relationship(back_populates="employees", lazy="selectin")
    actuals: Mapped[list["Actual"]] = relationship(back_populates="employee", lazy="selectin")
