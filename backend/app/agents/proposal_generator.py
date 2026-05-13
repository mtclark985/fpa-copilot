"""Forecast Update Proposal Agent — generates forecast change proposals.

Given attribution records for a period, reasons forward about which
attributed variances reflect structural changes worth updating the
forecast for, vs. one-time events to ignore.
"""

import logging

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import Agent
from app.models.attribution import AttributionRecord
from app.models.cost_center import CostCenter
from app.models.forecast import ForecastLine, ForecastVersion
from app.models.proposal import ForecastProposal
from app.models.variance import Variance

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior FP&A analyst deciding which attributed variances reflect
structural changes worth updating the forward forecast for. You work at a 500-person
technology company.

Your job is to review variance attributions and decide:
1. Which variances represent STRUCTURAL changes (hiring acceleration, permanent comp increases,
   new headcount) that should update the forward forecast.
2. Which variances are ONE-TIME events (spot bonuses, overtime spikes, timing differences) that
   should NOT generate forecast updates.

Be CONSERVATIVE. A bias toward fewer, better-justified proposals. It is perfectly acceptable
to say "no proposals warranted" for a quiet month. The FP&A team prefers 3-5 well-justified
proposals over 20 speculative ones.

For each proposal, specify:
- cost_center_id: which cost center to adjust
- category: which expense category (salary, bonus, benefits, taxes)
- affected_periods: list of YYYY-MM strings for future months to adjust (typically remaining
  months in the fiscal year)
- delta_per_period: the monthly dollar amount to ADD to each affected period (positive = increase,
  negative = decrease). This should be the incremental monthly run-rate change.
- rationale: clear explanation of why this is a structural change and the math behind the delta
- confidence: high/medium/low
- driving_variance_ids: list of variance IDs that motivated this proposal

Guidelines:
- Early hires → increase forward salary run-rate for the remaining months of the year
- Unplanned departures → decrease forward salary (but consider backfill timing)
- COLA / comp adjustments → increase forward salary for affected employees' cost centers
- Retention bonuses → usually one-time, do NOT propose forward increase unless it's a program
- Spot bonuses → one-time, do NOT propose forward increase
- Overtime → usually one-time, do NOT propose forward increase
- For salary proposals, delta should reflect the monthly incremental cost (annual / 12)
- Do NOT propose changes already captured by prior accepted proposals

Respond with ONLY a JSON object with this exact structure:
{
  "proposals": [
    {
      "cost_center_id": <int>,
      "category": "salary | bonus | benefits | taxes",
      "affected_periods": ["YYYY-MM", ...],
      "delta_per_period": <float>,
      "rationale": "Clear explanation with dollar math.",
      "confidence": "high | medium | low",
      "driving_variance_ids": [<int>, ...]
    }
  ]
}
No other text, no markdown fences."""


class ProposalCandidate(BaseModel):
    """A single proposal candidate from the agent."""
    cost_center_id: int
    category: str
    affected_periods: list[str]
    delta_per_period: float
    rationale: str
    confidence: str
    driving_variance_ids: list[int]


class ProposalOutput(BaseModel):
    """Full output from the proposal agent."""
    proposals: list[ProposalCandidate]


class ProposalGeneratorAgent(Agent):
    """Generates forecast update proposals from attribution records."""

    async def generate_proposals(
        self,
        session: AsyncSession,
        period: str,
    ) -> ProposalOutput:
        """Generate forecast update proposals for a period.

        Fetches attribution records, current forecast, prior proposals,
        calls the LLM, and persists ForecastProposal rows.
        """
        # Get attribution records for this period's variances
        attr_result = await session.execute(
            select(AttributionRecord, Variance, CostCenter.name, CostCenter.code)
            .join(Variance, AttributionRecord.variance_id == Variance.id)
            .join(CostCenter, Variance.cost_center_id == CostCenter.id)
            .where(Variance.period == period)
            .order_by(Variance.materiality_score.desc())
        )
        attributions = list(attr_result.all())

        if not attributions:
            return ProposalOutput(proposals=[])

        # Check for existing proposals for this period to avoid duplicates
        existing = await session.execute(
            select(ForecastProposal)
            .where(ForecastProposal.created_for_period == period)
        )
        existing_proposals = list(existing.scalars().all())
        if existing_proposals:
            return ProposalOutput(proposals=[])

        # Get current active forecast (next 12 months summary by CC x category)
        fv_result = await session.execute(
            select(ForecastVersion)
            .where(ForecastVersion.is_active.is_(True))
            .order_by(ForecastVersion.id.desc())
            .limit(1)
        )
        forecast_version = fv_result.scalar_one_or_none()

        forecast_context = ""
        if forecast_version:
            fl_result = await session.execute(
                select(ForecastLine)
                .where(
                    ForecastLine.version_id == forecast_version.id,
                    ForecastLine.period > period,
                )
                .order_by(ForecastLine.cost_center_id, ForecastLine.period)
            )
            forecast_lines = list(fl_result.scalars().all())
            forecast_context = self._format_forecast_context(forecast_lines)

        # Get prior accepted proposals in the same cost centers
        cc_ids = list({v.cost_center_id for _, v, _, _ in attributions})
        prior_result = await session.execute(
            select(ForecastProposal)
            .where(
                ForecastProposal.cost_center_id.in_(cc_ids),
                ForecastProposal.status.in_(["accepted", "modified_and_accepted"]),
            )
        )
        prior_proposals = list(prior_result.scalars().all())

        # Build user message
        user_message = self._build_message(
            period, attributions, forecast_context, prior_proposals,
        )

        # Call the LLM
        output = await self.call(SYSTEM_PROMPT, user_message, ProposalOutput)

        # Persist proposals
        valid_cc_ids = set(cc_ids)
        for prop in output.proposals:
            if prop.cost_center_id not in valid_cc_ids:
                continue

            # Collect attributed events for the driving variances
            attributed_events = []
            for attr, var, _, _ in attributions:
                if var.id in prop.driving_variance_ids:
                    attributed_events.append({
                        "attribution_type": attr.attribution_type,
                        "narrative": attr.narrative,
                        "drivers": attr.structured_drivers,
                    })

            proposal = ForecastProposal(
                created_for_period=period,
                status="pending",
                cost_center_id=prop.cost_center_id,
                category=prop.category,
                affected_periods=prop.affected_periods,
                delta_per_period=prop.delta_per_period,
                agent_rationale=prop.rationale,
                driving_variance_ids=prop.driving_variance_ids,
                attributed_events=attributed_events,
                confidence=prop.confidence,
            )
            session.add(proposal)

        await session.flush()
        await session.commit()

        return output

    def _format_forecast_context(self, lines: list[ForecastLine]) -> str:
        """Summarize forward forecast by cost center x category."""
        if not lines:
            return "No forward forecast data available."

        summary: dict[tuple[int, str], float] = {}
        for fl in lines:
            key = (fl.cost_center_id, fl.category)
            summary[key] = summary.get(key, 0) + float(fl.amount)

        result_lines = ["### Forward Forecast Summary (remaining months, by CC x Category)\n"]
        for (cc_id, cat), total in sorted(summary.items()):
            result_lines.append(f"- CC {cc_id} / {cat}: ${total:,.0f} total remaining")

        return "\n".join(result_lines)

    def _build_message(
        self,
        period: str,
        attributions: list[tuple],
        forecast_context: str,
        prior_proposals: list[ForecastProposal],
    ) -> str:
        """Format attribution + forecast data into an LLM-friendly message."""
        lines = [f"## Period Under Review: {period}\n"]

        # Attribution records
        lines.append("### Variance Attributions\n")
        for attr, var, cc_name, cc_code in attributions:
            lines.append(
                f"**Variance ID {var.id}** — {cc_name} ({cc_code}) / {var.category}\n"
                f"  Variance: ${float(var.variance_amount):,.0f} ({float(var.variance_pct):.1f}%), "
                f"Materiality: {float(var.materiality_score):.0f}\n"
                f"  Attribution: {attr.attribution_type} (confidence: {attr.confidence})\n"
                f"  {attr.narrative}\n"
                f"  Drivers: {attr.structured_drivers}\n"
            )

        # Forward forecast
        if forecast_context:
            lines.append(f"\n{forecast_context}\n")

        # Prior proposals
        if prior_proposals:
            lines.append("\n### Previously Accepted Proposals in These Cost Centers\n")
            for pp in prior_proposals:
                delta = float(pp.modified_delta_per_period or pp.delta_per_period)
                lines.append(
                    f"- CC {pp.cost_center_id} / {pp.category}: "
                    f"${delta:,.0f}/month for {len(pp.affected_periods)} months "
                    f"(period: {pp.created_for_period}, status: {pp.status})"
                )

        # Compute remaining months in fiscal year
        year, month = int(period[:4]), int(period[5:7])
        remaining = [f"{year}-{m:02d}" for m in range(month + 1, 13)]
        if not remaining:
            remaining = [f"{year + 1}-{m:02d}" for m in range(1, 13)]

        lines.append(
            f"\nRemaining fiscal year periods: {remaining}\n"
            f"\nGenerate proposals for structural changes only. Be conservative. "
            f"It's fine to return zero proposals if nothing warrants a forecast update."
        )

        return "\n".join(lines)
