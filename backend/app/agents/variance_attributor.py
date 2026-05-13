"""Variance Attribution Agent — traces material variances to specific drivers.

For each material variance, identifies the specific employees, positions,
or events that caused it (e.g., early hires, departures, comp adjustments).
"""

import datetime
import logging

from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import Agent
from app.models.actual import Actual
from app.models.attribution import AttributionRecord
from app.models.cost_center import CostCenter
from app.models.employee import Employee
from app.models.position import Position
from app.models.variance import Variance

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert FP&A analyst performing variance attribution for a 500-person
technology company. Your job is to link each material compensation expense variance to specific,
concrete drivers — not vague generalizations.

For each variance you are given, identify the specific cause(s):
- **early_hire**: A position was filled earlier than planned
- **late_hire**: A position was filled later than planned (favorable variance)
- **unplanned_hire**: A hire not in the original headcount plan
- **unplanned_departure**: An employee left unexpectedly
- **comp_adjustment**: Off-cycle salary adjustment, COLA, or market rate correction
- **bonus_event**: Retention bonus, spot bonus, or bonus accrual variance
- **other**: Anything else (overtime, contractor conversion, etc.)

Guidelines:
- Be SPECIFIC. Reference real employee IDs and names, real position IDs, real cost center codes.
- Each attribution should have a clear narrative explaining the causal chain.
- If a variance is driven by multiple factors, pick the dominant one for attribution_type but
  mention all factors in the narrative.
- Confidence should be 'high' when the data clearly supports the attribution, 'medium' when
  it's a reasonable inference, 'low' when the driver is uncertain.
- Not every variance can be attributed — if you cannot identify a specific driver, omit it.
  Only return attributions where you have at least medium confidence.

Respond with ONLY a JSON object with this exact structure:
{
  "attributions": [
    {
      "variance_id": <int>,
      "attribution_type": "early_hire | late_hire | unplanned_hire | unplanned_departure | comp_adjustment | bonus_event | other",
      "narrative": "One paragraph explaining what happened and why it caused this variance.",
      "structured_drivers": [
        {"type": "hire", "employee_id": <int>, "employee_name": "...", "details": "..."},
        ...
      ],
      "confidence": "high | medium | low"
    }
  ]
}
No other text, no markdown fences."""


class DriverDetail(BaseModel):
    """A single structured driver within an attribution."""
    type: str
    employee_id: int | None = None
    employee_name: str | None = None
    details: str = ""


class AttributionItem(BaseModel):
    """Attribution for a single variance."""
    variance_id: int
    attribution_type: str
    narrative: str
    structured_drivers: list[DriverDetail]
    confidence: str


class AttributionOutput(BaseModel):
    """Full output from the attribution agent."""
    attributions: list[AttributionItem]


class VarianceAttributorAgent(Agent):
    """Traces material variances to specific drivers."""

    async def analyze_period(
        self,
        session: AsyncSession,
        period: str,
    ) -> AttributionOutput:
        """Attribute material variances for a period to specific drivers.

        Fetches variances, employee/position context, calls the LLM,
        and persists AttributionRecord rows.
        """
        # Get material variances (severity >= medium OR materiality_score >= 50)
        result = await session.execute(
            select(Variance, CostCenter.name, CostCenter.code)
            .join(CostCenter, Variance.cost_center_id == CostCenter.id)
            .where(
                Variance.period == period,
                Variance.materiality_score >= 50,
            )
            .order_by(Variance.materiality_score.desc())
            .limit(25)
        )
        material_variances = list(result.all())

        if not material_variances:
            return AttributionOutput(attributions=[])

        # Check for existing attributions to avoid duplicates
        variance_ids = [v.id for v, _, _ in material_variances]
        existing = await session.execute(
            select(AttributionRecord.variance_id)
            .where(AttributionRecord.variance_id.in_(variance_ids))
        )
        already_attributed = set(existing.scalars().all())
        material_variances = [
            (v, cc_name, cc_code) for v, cc_name, cc_code in material_variances
            if v.id not in already_attributed
        ]

        if not material_variances:
            return AttributionOutput(attributions=[])

        # Get cost center IDs for context
        cc_ids = list({v.cost_center_id for v, _, _ in material_variances})

        # Get employees in affected cost centers (hires, departures, active)
        year, month = int(period[:4]), int(period[5:7])
        period_start = datetime.date(year, month, 1)
        if month == 12:
            period_end = datetime.date(year, 12, 31)
        else:
            period_end = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)

        # Hires this period
        hires_result = await session.execute(
            select(Employee)
            .where(
                Employee.cost_center_id.in_(cc_ids),
                Employee.hire_date >= period_start,
                Employee.hire_date <= period_end,
            )
        )
        hires = list(hires_result.scalars().all())

        # Departures this period
        deps_result = await session.execute(
            select(Employee)
            .where(
                Employee.cost_center_id.in_(cc_ids),
                Employee.termination_date >= period_start,
                Employee.termination_date <= period_end,
            )
        )
        departures = list(deps_result.scalars().all())

        # Open positions in affected cost centers
        positions_result = await session.execute(
            select(Position)
            .where(
                Position.cost_center_id.in_(cc_ids),
                Position.status == "open",
            )
        )
        open_positions = list(positions_result.scalars().all())

        # Get headcount per cost center for context
        hc_result = await session.execute(
            select(Employee.cost_center_id, func.count(Employee.id))
            .where(
                Employee.cost_center_id.in_(cc_ids),
                Employee.hire_date <= period_end,
                (Employee.termination_date.is_(None)) | (Employee.termination_date > period_start),
            )
            .group_by(Employee.cost_center_id)
        )
        hc_by_cc = {row[0]: row[1] for row in hc_result.all()}

        # Build user message
        user_message = self._build_message(
            period, material_variances, hires, departures,
            open_positions, hc_by_cc,
        )

        # Call the LLM
        output = await self.call(SYSTEM_PROMPT, user_message, AttributionOutput)

        # Persist AttributionRecord rows
        valid_variance_ids = {v.id for v, _, _ in material_variances}
        for attr in output.attributions:
            if attr.variance_id not in valid_variance_ids:
                continue
            record = AttributionRecord(
                variance_id=attr.variance_id,
                attribution_type=attr.attribution_type,
                narrative=attr.narrative,
                structured_drivers=[d.model_dump() for d in attr.structured_drivers],
                confidence=attr.confidence,
            )
            session.add(record)

        await session.flush()
        await session.commit()

        return output

    def _build_message(
        self,
        period: str,
        variances: list[tuple],
        hires: list[Employee],
        departures: list[Employee],
        open_positions: list[Position],
        hc_by_cc: dict[int, int],
    ) -> str:
        """Format variance + employee data into an LLM-friendly message."""
        lines = [f"## Period: {period}\n"]

        # Material variances
        lines.append("### Material Variances\n")
        lines.append("| ID | Cost Center | CC Code | Category | Forecast | Actual | Variance $ | Variance % | Volume Var | Rate Var | Materiality | Severity |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for v, cc_name, cc_code in variances:
            lines.append(
                f"| {v.id} | {cc_name} | {cc_code} | {v.category} | "
                f"${float(v.forecast_amount):,.0f} | ${float(v.actual_amount):,.0f} | "
                f"${float(v.variance_amount):,.0f} | {float(v.variance_pct):.1f}% | "
                f"${float(v.volume_variance):,.0f} | ${float(v.rate_variance):,.0f} | "
                f"{float(v.materiality_score):.0f} | {v.agent_severity or 'n/a'} |"
            )

        # Hires
        if hires:
            lines.append(f"\n### New Hires This Period ({len(hires)})\n")
            for emp in hires:
                lines.append(
                    f"- Employee ID {emp.id} ({emp.name}): {emp.job_level}, "
                    f"CC {emp.cost_center_id}, hired {emp.hire_date}, "
                    f"salary ${float(emp.base_salary):,.0f}, location {emp.location}"
                )

        # Departures
        if departures:
            lines.append(f"\n### Departures This Period ({len(departures)})\n")
            for emp in departures:
                lines.append(
                    f"- Employee ID {emp.id} ({emp.name}): {emp.job_level}, "
                    f"CC {emp.cost_center_id}, terminated {emp.termination_date}, "
                    f"salary ${float(emp.base_salary):,.0f}"
                )

        # Open positions
        if open_positions:
            lines.append(f"\n### Open Positions ({len(open_positions)})\n")
            for pos in open_positions:
                lines.append(
                    f"- Position ID {pos.id}: CC {pos.cost_center_id}, "
                    f"{pos.job_level}, target start {pos.target_start_date}"
                )

        # Headcount by CC
        lines.append("\n### Headcount by Cost Center\n")
        for cc_id, hc in sorted(hc_by_cc.items()):
            lines.append(f"- CC {cc_id}: {hc} employees")

        lines.append(f"\nAttribute each variance to its specific driver(s). "
                     f"Reference real employee IDs and names from the data above. "
                     f"Only attribute variances where you can identify a concrete driver.")

        return "\n".join(lines)
