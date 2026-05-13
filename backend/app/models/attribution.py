"""Attribution record — structured output from the Variance Attribution Agent."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.variance import Variance


class AttributionRecord(Base):
    """Links a variance to specific drivers identified by the attribution agent."""

    __tablename__ = "attribution_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    variance_id: Mapped[int] = mapped_column(ForeignKey("variances.id"), index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.utcnow
    )
    attribution_type: Mapped[str] = mapped_column(String(30))
    narrative: Mapped[str] = mapped_column(Text)
    structured_drivers: Mapped[Any] = mapped_column(JSON, default=list)
    confidence: Mapped[str] = mapped_column(String(10))

    variance: Mapped["Variance"] = relationship(
        back_populates="attributions", lazy="selectin"
    )
