"""Forecast models — versioned forecast with line items."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.cost_center import CostCenter
    from app.models.variance import Variance


class ForecastVersion(Base):
    """A named snapshot of the forecast — only one is active at a time."""

    __tablename__ = "forecast_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.utcnow
    )
    is_active: Mapped[bool] = mapped_column(default=True)

    lines: Mapped[list["ForecastLine"]] = relationship(
        back_populates="version", lazy="selectin"
    )
    variances: Mapped[list["Variance"]] = relationship(
        back_populates="forecast_version", lazy="selectin"
    )


class ForecastLine(Base):
    """Single forecast line: one cost center, one month, one category."""

    __tablename__ = "forecast_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("forecast_versions.id"), index=True)
    cost_center_id: Mapped[int] = mapped_column(ForeignKey("cost_centers.id"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)  # YYYY-MM
    category: Mapped[str] = mapped_column(String(20))  # salary/bonus/benefits/taxes
    amount: Mapped[float] = mapped_column(Numeric(14, 2))
    headcount_eop: Mapped[int] = mapped_column(default=0)

    version: Mapped["ForecastVersion"] = relationship(back_populates="lines", lazy="selectin")
    cost_center: Mapped["CostCenter"] = relationship(
        back_populates="forecast_lines", lazy="selectin"
    )
