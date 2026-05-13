"""Position model — open or filled headcount slot."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.cost_center import CostCenter


class Position(Base):
    """Tracks open and filled positions for headcount planning."""

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    cost_center_id: Mapped[int] = mapped_column(ForeignKey("cost_centers.id"), index=True)
    job_level: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(10))  # open / filled
    target_start_date: Mapped[datetime.date]

    cost_center: Mapped["CostCenter"] = relationship(back_populates="positions", lazy="selectin")
