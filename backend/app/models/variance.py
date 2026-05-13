"""Variance model — forecast-vs-actual variance with agent assessment."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.cost_center import CostCenter
    from app.models.forecast import ForecastVersion


class Variance(Base):
    """Calculated variance with optional AI agent assessment."""

    __tablename__ = "variances"

    id: Mapped[int] = mapped_column(primary_key=True)
    forecast_version_id: Mapped[int] = mapped_column(
        ForeignKey("forecast_versions.id"), index=True
    )
    cost_center_id: Mapped[int] = mapped_column(ForeignKey("cost_centers.id"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    category: Mapped[str] = mapped_column(String(20))
    forecast_amount: Mapped[float] = mapped_column(Numeric(14, 2))
    actual_amount: Mapped[float] = mapped_column(Numeric(14, 2))
    variance_amount: Mapped[float] = mapped_column(Numeric(14, 2))
    variance_pct: Mapped[float] = mapped_column(Numeric(8, 4))
    volume_variance: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    rate_variance: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    materiality_score: Mapped[float] = mapped_column(Numeric(5, 1), default=0)
    detected_at: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.utcnow
    )

    # Agent assessment fields — populated by variance detection agent
    agent_severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    agent_unexpectedness: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    agent_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agent_suggested_action: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    forecast_version: Mapped["ForecastVersion"] = relationship(
        back_populates="variances", lazy="selectin"
    )
    cost_center: Mapped["CostCenter"] = relationship(
        back_populates="variances", lazy="selectin"
    )
