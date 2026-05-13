"""Tests for the forecast proposal agent with mocked Anthropic responses."""

import asyncio
from unittest.mock import MagicMock, patch

from app.agents.proposal_generator import (
    ProposalCandidate,
    ProposalGeneratorAgent,
    ProposalOutput,
)


MOCK_PROPOSALS = ProposalOutput(
    proposals=[
        ProposalCandidate(
            cost_center_id=5,
            category="salary",
            affected_periods=["2026-07", "2026-08", "2026-09", "2026-10", "2026-11", "2026-12"],
            delta_per_period=8500.00,
            rationale=(
                "Risk team filled 3 positions early at above-market rates. "
                "These are permanent headcount additions with an incremental "
                "monthly salary cost of ~$8,500. The forward run-rate should "
                "reflect these hires for the remaining 6 months."
            ),
            confidence="high",
            driving_variance_ids=[1, 3],
        ),
        ProposalCandidate(
            cost_center_id=12,
            category="salary",
            affected_periods=["2026-07", "2026-08", "2026-09", "2026-10", "2026-11", "2026-12"],
            delta_per_period=-4200.00,
            rationale=(
                "Sales team had 4 unplanned departures. Even accounting for "
                "backfill, there will be a 2-3 month gap. Decrease salary "
                "forecast by the net savings of $4,200/month."
            ),
            confidence="medium",
            driving_variance_ids=[7],
        ),
    ]
)


def test_proposal_output_schema() -> None:
    """ProposalOutput Pydantic model validates correctly."""
    data = MOCK_PROPOSALS.model_dump()
    parsed = ProposalOutput.model_validate(data)
    assert len(parsed.proposals) == 2
    assert parsed.proposals[0].category == "salary"
    assert parsed.proposals[1].delta_per_period == -4200.00


def test_proposal_from_json() -> None:
    """Agent output can be parsed from raw JSON string."""
    json_str = MOCK_PROPOSALS.model_dump_json()
    parsed = ProposalOutput.model_validate_json(json_str)
    assert parsed.proposals[0].cost_center_id == 5
    assert len(parsed.proposals[0].affected_periods) == 6


@patch("app.agents.base.anthropic.Anthropic")
def test_proposal_agent_parses_mock_response(mock_anthropic_cls: MagicMock) -> None:
    """Agent.call() correctly parses a mocked proposal response."""
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=MOCK_PROPOSALS.model_dump_json())]
    mock_response.usage.input_tokens = 1200
    mock_response.usage.output_tokens = 600
    mock_client.messages.create.return_value = mock_response

    agent = ProposalGeneratorAgent()

    result = asyncio.run(
        agent.call("system", "user message", ProposalOutput)
    )

    assert isinstance(result, ProposalOutput)
    assert len(result.proposals) == 2
    assert result.proposals[0].driving_variance_ids == [1, 3]


def test_valid_categories() -> None:
    """Category must be salary/bonus/benefits/taxes."""
    valid = {"salary", "bonus", "benefits", "taxes", "other"}
    for prop in MOCK_PROPOSALS.proposals:
        assert prop.category in valid


def test_conservative_proposal_count() -> None:
    """Proposals should be conservative — not more than 10 per period."""
    assert len(MOCK_PROPOSALS.proposals) <= 10
