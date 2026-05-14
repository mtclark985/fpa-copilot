"""Shared agent infrastructure — wraps Anthropic API calls.

Every agent inherits from this base class, which provides standardized
prompt formatting, Pydantic output parsing, and call logging.
"""

import json
import logging
from typing import TypeVar

import anthropic
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class AgentOutputError(Exception):
    """Raised when the agent's response cannot be parsed as valid JSON."""

    def __init__(self, message: str, raw_response: str) -> None:
        super().__init__(message)
        self.raw_response = raw_response


class Agent:
    """Base class for AI agents that call the Anthropic API.

    Each subclass defines its own system prompt, context builder,
    and output model. The base class handles the API call mechanics.
    """

    model: str = "claude-sonnet-4-6"
    max_tokens: int = 16384

    def __init__(self) -> None:
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def _extract_json(self, raw_text: str) -> str:
        """Extract JSON from response text, stripping markdown fences if present."""
        json_text = raw_text.strip()
        if json_text.startswith("```"):
            lines = json_text.split("\n")
            json_text = "\n".join(lines[1:-1])
        return json_text

    async def call(
        self,
        system_prompt: str,
        user_message: str,
        output_type: type[T],
    ) -> T:
        """Make an Anthropic API call and parse the response into a Pydantic model.

        Uses synchronous client in an async context because the anthropic SDK's
        async client adds complexity with minimal benefit for single calls.

        On JSON parse failure, retries once with doubled max_tokens before raising.
        """
        logger.info(
            "Agent call: model=%s, output_type=%s, prompt_len=%d",
            self.model,
            output_type.__name__,
            len(user_message),
        )

        raw_text = self._make_api_call(system_prompt, user_message, self.max_tokens)
        json_text = self._extract_json(raw_text)

        try:
            parsed = json.loads(json_text)
            return output_type.model_validate(parsed)
        except (json.JSONDecodeError, Exception) as first_error:
            truncated = raw_text[:500]
            logger.warning(
                "Agent JSON parse failed (first attempt), retrying with doubled max_tokens. "
                "Error: %s. Raw response (truncated): %s",
                first_error,
                truncated,
            )

            # Retry with doubled max_tokens
            retry_max_tokens = self.max_tokens * 2
            raw_text_retry = self._make_api_call(
                system_prompt, user_message, retry_max_tokens
            )
            json_text_retry = self._extract_json(raw_text_retry)

            try:
                parsed = json.loads(json_text_retry)
                return output_type.model_validate(parsed)
            except (json.JSONDecodeError, Exception) as retry_error:
                truncated_retry = raw_text_retry[:500]
                logger.error(
                    "Agent JSON parse failed on retry. Error: %s. "
                    "Raw response (truncated): %s",
                    retry_error,
                    truncated_retry,
                )
                raise AgentOutputError(
                    f"Failed to parse agent output after retry: {retry_error}",
                    raw_response=raw_text_retry,
                ) from retry_error

    def _make_api_call(
        self, system_prompt: str, user_message: str, max_tokens: int
    ) -> str:
        """Make a single API call and return the raw text response."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = response.content[0].text
        logger.info(
            "Agent response: tokens_in=%d, tokens_out=%d",
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        return raw_text
