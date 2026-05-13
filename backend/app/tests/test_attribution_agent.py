"""Tests for the variance attribution agent with mocked Anthropic responses."""

import asyncio
import json
from unittest.mock import MagicMock, patch

from app.agents.variance_attributor import (
    AttributionItem,
    AttributionOutput,
    DriverDetail,
    VarianceAttributorAgent,
)


MOCK_ATTRIBUTION = AttributionOutput(
    attributions=[
        AttributionItem(
            variance_id=1,
            attribution_type="early_hire",
            narrative=(
                "Risk team filled position REQ-1041 (Employee ID 412, Jane Smith) "
                "in January, 60 days ahead of the planned March start. This added "
                "approximately $8,500 in unplanned salary expense for the period."
            ),
            structured_drivers=[
                DriverDetail(
                    type="hire",
                    employee_id=412,
                    employee_name="Jane Smith",
                    details="Hired 2026-01-15, planned 2026-03-01",
                ),
            ],
            confidence="high",
        ),
        AttributionItem(
            variance_id=2,
            attribution_type="unplanned_departure",
            narrative=(
                "Senior engineer (Employee ID 203, Bob Jones) departed unexpectedly "
                "mid-month, resulting in a favorable salary variance offset by "
                "severance accrual."
            ),
            structured_drivers=[
                DriverDetail(
                    type="departure",
                    employee_id=203,
                    employee_name="Bob Jones",
                    details="Terminated 2026-01-18, L6 engineer",
                ),
            ],
            confidence="medium",
        ),
    ]
)


def test_attribution_output_schema() -> None:
    """AttributionOutput Pydantic model validates correctly."""
    data = MOCK_ATTRIBUTION.model_dump()
    parsed = AttributionOutput.model_validate(data)
    assert len(parsed.attributions) == 2
    assert parsed.attributions[0].attribution_type == "early_hire"
    assert parsed.attributions[1].confidence == "medium"


def test_attribution_from_json() -> None:
    """Agent output can be parsed from raw JSON string."""
    json_str = MOCK_ATTRIBUTION.model_dump_json()
    parsed = AttributionOutput.model_validate_json(json_str)
    assert parsed.attributions[0].variance_id == 1
    assert len(parsed.attributions[0].structured_drivers) == 1


@patch("app.agents.base.anthropic.Anthropic")
def test_attributor_parses_mock_response(mock_anthropic_cls: MagicMock) -> None:
    """Agent.call() correctly parses a mocked attribution response."""
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=MOCK_ATTRIBUTION.model_dump_json())]
    mock_response.usage.input_tokens = 800
    mock_response.usage.output_tokens = 400
    mock_client.messages.create.return_value = mock_response

    agent = VarianceAttributorAgent()

    result = asyncio.run(
        agent.call("system", "user message", AttributionOutput)
    )

    assert isinstance(result, AttributionOutput)
    assert len(result.attributions) == 2
    assert result.attributions[0].structured_drivers[0].employee_id == 412


def test_valid_attribution_types() -> None:
    """Attribution type must be one of the defined values."""
    valid = {
        "early_hire", "late_hire", "unplanned_hire",
        "unplanned_departure", "comp_adjustment", "bonus_event", "other",
    }
    for attr in MOCK_ATTRIBUTION.attributions:
        assert attr.attribution_type in valid


def test_valid_confidence_values() -> None:
    """Confidence must be high/medium/low."""
    valid = {"high", "medium", "low"}
    for attr in MOCK_ATTRIBUTION.attributions:
        assert attr.confidence in valid
