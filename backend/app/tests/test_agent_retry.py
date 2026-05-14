"""Tests for the agent base class retry and error handling logic."""

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from app.agents.base import Agent, AgentOutputError
from app.agents.variance_detector import VarianceAssessment


VALID_JSON = json.dumps({
    "period": "2026-01",
    "summary": "Test summary.",
    "assessments": [],
})


def _mock_response(text: str) -> MagicMock:
    """Build a mock Anthropic response with the given text."""
    resp = MagicMock()
    resp.content = [MagicMock(text=text)]
    resp.usage.input_tokens = 100
    resp.usage.output_tokens = 50
    return resp


@patch("app.agents.base.anthropic.Anthropic")
def test_retry_on_invalid_json_first_attempt(mock_cls: MagicMock) -> None:
    """When first response is invalid JSON, agent retries and succeeds."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    # First call returns invalid JSON, second returns valid
    mock_client.messages.create.side_effect = [
        _mock_response("not valid json {{{"),
        _mock_response(VALID_JSON),
    ]

    agent = Agent()
    result = asyncio.run(
        agent.call("system", "user", VarianceAssessment)
    )

    assert isinstance(result, VarianceAssessment)
    assert result.period == "2026-01"
    # Verify two API calls were made
    assert mock_client.messages.create.call_count == 2
    # Verify retry used doubled max_tokens
    first_call_tokens = mock_client.messages.create.call_args_list[0].kwargs["max_tokens"]
    second_call_tokens = mock_client.messages.create.call_args_list[1].kwargs["max_tokens"]
    assert second_call_tokens == first_call_tokens * 2


@patch("app.agents.base.anthropic.Anthropic")
def test_raises_agent_output_error_after_both_failures(mock_cls: MagicMock) -> None:
    """When both attempts fail JSON parsing, AgentOutputError is raised."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    mock_client.messages.create.side_effect = [
        _mock_response("bad json attempt 1"),
        _mock_response("bad json attempt 2"),
    ]

    agent = Agent()
    with pytest.raises(AgentOutputError) as exc_info:
        asyncio.run(agent.call("system", "user", VarianceAssessment))

    assert "bad json attempt 2" in exc_info.value.raw_response


@patch("app.agents.base.anthropic.Anthropic")
def test_no_retry_on_valid_first_response(mock_cls: MagicMock) -> None:
    """Valid JSON on first attempt doesn't trigger retry."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    mock_client.messages.create.return_value = _mock_response(VALID_JSON)

    agent = Agent()
    result = asyncio.run(
        agent.call("system", "user", VarianceAssessment)
    )

    assert isinstance(result, VarianceAssessment)
    assert mock_client.messages.create.call_count == 1


@patch("app.agents.base.anthropic.Anthropic")
def test_retry_on_truncated_json(mock_cls: MagicMock) -> None:
    """Truncated JSON (common with low max_tokens) triggers retry."""
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    truncated = '{"period": "2026-01", "summary": "Test", "assessments": ['
    mock_client.messages.create.side_effect = [
        _mock_response(truncated),
        _mock_response(VALID_JSON),
    ]

    agent = Agent()
    result = asyncio.run(
        agent.call("system", "user", VarianceAssessment)
    )

    assert isinstance(result, VarianceAssessment)
    assert mock_client.messages.create.call_count == 2
