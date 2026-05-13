"""Variance Detection Agent — flags material and unexpected variances.

Reviews calculated variances for a period and produces structured
assessments of which variances deserve human attention, with reasoning.
"""

import logging

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import Agent
from app.models.variance import Variance

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an experienced FP&A analyst reviewing month-end compensation
expense variances. You work at a 500-person technology company.

Your job is to assess each variance and determine:
1. Severity: how significant is this variance? (low / medium / high)
2. Unexpectedness: was this expected or surprising? (expected / somewhat_unexpected / highly_unexpected)
3. Rationale: a concise one-sentence explanation of what likely drove this variance
4. Suggested action: what should the FP&A team do? (monitor / investigate / escalate)

Guidelines:
- Salary variances driven by headcount changes (volume variance) are more expected than
  rate variances, which suggest off-cycle compensation changes.
- Small variances (<2%) in line items under $50K are noise — mark as low/expected/monitor.
- Large headcount variances in specific cost centers suggest unplanned hiring or departures.
- Bonus actuals that significantly exceed accruals suggest off-cycle bonuses.
- Consider patterns: if a cost center consistently overruns, that's a systemic issue worth escalating.

Respond with ONLY a JSON object with this exact structure:
{
  "period": "YYYY-MM (the period being analyzed)",
  "summary": "2-3 sentence executive summary of the period's variance picture: total magnitude, key themes, biggest concern.",
  "assessments": [
    {
      "variance_id": <int>,
      "severity": "low | medium | high",
      "unexpectedness": "expected | somewhat_unexpected | highly_unexpected",
      "rationale": "concise one-sentence explanation",
      "suggested_action": "monitor | investigate | escalate"
    }
  ]
}
No other text, no markdown fences."""


class VarianceItemAssessment(BaseModel):
    """Assessment for a single variance line."""

    variance_id: int
    severity: str  # low / medium / high
    unexpectedness: str  # expected / somewhat_unexpected / highly_unexpected
    rationale: str
    suggested_action: str  # monitor / investigate / escalate


class VarianceAssessment(BaseModel):
    """Full assessment output from the variance detection agent."""

    period: str
    summary: str
    assessments: list[VarianceItemAssessment]


class VarianceDetectorAgent(Agent):
    """Reviews variances and produces structured assessments."""

    async def analyze_period(
        self,
        session: AsyncSession,
        period: str,
    ) -> VarianceAssessment:
        """Analyze all material variances for a period.

        Fetches variances, builds context with prior months, calls the LLM,
        and persists the assessment back to variance records.
        """
        # Get current period variances (materiality >= 30 to focus on meaningful ones)
        result = await session.execute(
            select(Variance)
            .where(Variance.period == period, Variance.materiality_score >= 30)
            .order_by(Variance.materiality_score.desc())
            .limit(30)
        )
        current_variances = list(result.scalars().all())

        if not current_variances:
            return VarianceAssessment(
                period=period,
                summary="No material variances found.",
                assessments=[],
            )

        # Get prior 3 months for context
        year, month = int(period[:4]), int(period[5:7])
        prior_periods = []
        for i in range(1, 4):
            pm = month - i
            py = year
            if pm <= 0:
                pm += 12
                py -= 1
            prior_periods.append(f"{py:04d}-{pm:02d}")

        prior_result = await session.execute(
            select(Variance)
            .where(Variance.period.in_(prior_periods), Variance.materiality_score >= 40)
            .order_by(Variance.period, Variance.materiality_score.desc())
        )
        prior_variances = list(prior_result.scalars().all())

        # Build user message
        user_message = self._build_message(period, current_variances, prior_variances)

        # Call the LLM
        assessment = await self.call(SYSTEM_PROMPT, user_message, VarianceAssessment)

        # Persist assessments back to variance records
        assessment_lookup = {a.variance_id: a for a in assessment.assessments}
        for var in current_variances:
            if var.id in assessment_lookup:
                a = assessment_lookup[var.id]
                var.agent_severity = a.severity
                var.agent_unexpectedness = a.unexpectedness
                var.agent_rationale = a.rationale
                var.agent_suggested_action = a.suggested_action

        await session.flush()
        await session.commit()

        return assessment

    def _build_message(
        self,
        period: str,
        current: list[Variance],
        prior: list[Variance],
    ) -> str:
        """Format variance data into an LLM-friendly message."""
        lines = [f"## Current Period: {period}\n"]
        lines.append("| ID | Cost Center | Category | Forecast | Actual | Variance $ | Variance % | Volume Var | Rate Var | Materiality |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|")

        for v in current:
            lines.append(
                f"| {v.id} | CC-{v.cost_center_id} | {v.category} | "
                f"${float(v.forecast_amount):,.0f} | ${float(v.actual_amount):,.0f} | "
                f"${float(v.variance_amount):,.0f} | {float(v.variance_pct):.1f}% | "
                f"${float(v.volume_variance):,.0f} | ${float(v.rate_variance):,.0f} | "
                f"{float(v.materiality_score):.0f} |"
            )

        if prior:
            lines.append(f"\n## Prior Period Context (last 3 months, material variances only)\n")
            for v in prior:
                lines.append(
                    f"- {v.period} CC-{v.cost_center_id} {v.category}: "
                    f"${float(v.variance_amount):,.0f} ({float(v.variance_pct):.1f}%)"
                )

        lines.append(f"\nAnalyze all {len(current)} variances for period {period}.")
        lines.append(f"Return a JSON object with period='{period}', a 2-3 sentence summary, and an assessment for each variance_id listed above.")

        return "\n".join(lines)
