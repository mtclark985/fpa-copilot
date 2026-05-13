"""Cost center model — organizational unit for budgeting."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.forecast import ForecastLine
    from app.models.position import Position
    from app.models.variance import Variance


class CostCenter(Base):
    """Represents an organizational cost center in the company hierarchy."""

    __tablename__ = "cost_centers"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("cost_centers.id"), index=True, nullable=True
    )
    vp_owner: Mapped[str] = mapped_column(String(200))

    parent: Mapped[Optional["CostCenter"]] = relationship(
        "CostCenter", remote_side="CostCenter.id", lazy="selectin"
    )
    employees: Mapped[list["Employee"]] = relationship(
        back_populates="cost_center", lazy="selectin"
    )
    positions: Mapped[list["Position"]] = relationship(
        back_populates="cost_center", lazy="selectin"
    )
    forecast_lines: Mapped[list["ForecastLine"]] = relationship(
        back_populates="cost_center", lazy="selectin"
    )
    variances: Mapped[list["Variance"]] = relationship(
        back_populates="cost_center", lazy="selectin"
    )
