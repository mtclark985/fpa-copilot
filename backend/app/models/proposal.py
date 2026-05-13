"""Forecast proposal models — proposals and audit trail."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.cost_center import CostCenter
    from app.models.forecast import ForecastVersion


class ForecastProposal(Base):
    """A specific change to the forecast, proposed by an agent, awaiting human decision."""

    __tablename__ = "forecast_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.utcnow
    )
    created_for_period: Mapped[str] = mapped_column(String(7))
    status: Mapped[str] = mapped_column(String(30), default="pending")

    # What's being proposed
    cost_center_id: Mapped[int] = mapped_column(ForeignKey("cost_centers.id"), index=True)
    category: Mapped[str] = mapped_column(String(20))
    affected_periods: Mapped[Any] = mapped_column(JSON, default=list)
    delta_per_period: Mapped[float] = mapped_column(Numeric(14, 2))

    # Why
    agent_rationale: Mapped[str] = mapped_column(Text)
    driving_variance_ids: Mapped[Any] = mapped_column(JSON, default=list)
    attributed_events: Mapped[Any] = mapped_column(JSON, default=list)
    confidence: Mapped[str] = mapped_column(String(10))

    # Decision metadata
    decided_at: Mapped[Optional[datetime.datetime]] = mapped_column(nullable=True)
    decided_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    decision_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    modified_delta_per_period: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 2), nullable=True
    )

    # Linkage to applied ForecastVersion
    resulting_forecast_version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("forecast_versions.id"), nullable=True
    )

    cost_center: Mapped["CostCenter"] = relationship(lazy="selectin")
    resulting_forecast_version: Mapped[Optional["ForecastVersion"]] = relationship(
        foreign_keys=[resulting_forecast_version_id], lazy="selectin"
    )
    audit_entries: Mapped[list["ProposalDecisionAudit"]] = relationship(
        back_populates="proposal", lazy="selectin"
    )


class ProposalDecisionAudit(Base):
    """Append-only log of every decision made on a proposal."""

    __tablename__ = "proposal_decision_audits"

    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_id: Mapped[int] = mapped_column(
        ForeignKey("forecast_proposals.id"), index=True
    )
    occurred_at: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.utcnow
    )
    from_status: Mapped[str] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30))
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delta_change: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)

    proposal: Mapped["ForecastProposal"] = relationship(
        back_populates="audit_entries", lazy="selectin"
    )
