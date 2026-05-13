"""Tests for the variance detection agent with mocked Anthropic responses.

Uses a fixture cassette instead of real API calls to avoid burning tokens.
"""

import json
from unittest.mock import MagicMock, patch

from app.agents.variance_detector import (
    VarianceAssessment,
    VarianceDetectorAgent,
    VarianceItemAssessment,
)


MOCK_ASSESSMENT = VarianceAssessment(
    period="2026-01",
    summary="January showed elevated hiring in Corporate division with above-market rates.",
    assessments=[
        VarianceItemAssessment(
            variance_id=1,
            severity="high",
            unexpectedness="highly_unexpected",
            rationale="Risk team backfilled 3 positions early at premium rates, driving both volume and rate variance.",
            suggested_action="escalate",
        ),
        VarianceItemAssessment(
            variance_id=2,
            severity="low",
            unexpectedness="expected",
            rationale="Normal monthly payroll variance within tolerance.",
            suggested_action="monitor",
        ),
    ],
)


def test_variance_assessment_schema() -> None:
    """VarianceAssessment Pydantic model validates correctly."""
    data = MOCK_ASSESSMENT.model_dump()
    parsed = VarianceAssessment.model_validate(data)
    assert len(parsed.assessments) == 2
    assert parsed.assessments[0].severity == "high"
    assert parsed.assessments[1].suggested_action == "monitor"


def test_assessment_from_json() -> None:
    """Agent output can be parsed from raw JSON string."""
    json_str = MOCK_ASSESSMENT.model_dump_json()
    parsed = VarianceAssessment.model_validate_json(json_str)
    assert parsed.period == "2026-01"
    assert parsed.assessments[0].unexpectedness == "highly_unexpected"


@patch("app.agents.base.anthropic.Anthropic")
def test_agent_parses_mock_response(mock_anthropic_cls: MagicMock) -> None:
    """Agent.call() correctly parses a mocked Anthropic API response."""
    # Set up mock chain
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=MOCK_ASSESSMENT.model_dump_json())]
    mock_response.usage.input_tokens = 500
    mock_response.usage.output_tokens = 200
    mock_client.messages.create.return_value = mock_response

    agent = VarianceDetectorAgent()

    import asyncio
    result = asyncio.run(
        agent.call("system", "user message", VarianceAssessment)
    )

    assert isinstance(result, VarianceAssessment)
    assert result.period == "2026-01"
    assert len(result.assessments) == 2


def test_valid_severity_values() -> None:
    """Severity must be low/medium/high."""
    valid = {"low", "medium", "high"}
    for assessment in MOCK_ASSESSMENT.assessments:
        assert assessment.severity in valid


def test_valid_action_values() -> None:
    """Suggested action must be monitor/investigate/escalate."""
    valid = {"monitor", "investigate", "escalate"}
    for assessment in MOCK_ASSESSMENT.assessments:
        assert assessment.suggested_action in valid
