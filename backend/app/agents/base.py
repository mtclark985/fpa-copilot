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


class Agent:
    """Base class for AI agents that call the Anthropic API.

    Each subclass defines its own system prompt, context builder,
    and output model. The base class handles the API call mechanics.
    """

    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096

    def __init__(self) -> None:
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    async def call(
        self,
        system_prompt: str,
        user_message: str,
        output_type: type[T],
    ) -> T:
        """Make an Anthropic API call and parse the response into a Pydantic model.

        Uses synchronous client in an async context because the anthropic SDK's
        async client adds complexity with minimal benefit for single calls.
        """
        logger.info(
            "Agent call: model=%s, output_type=%s, prompt_len=%d",
            self.model,
            output_type.__name__,
            len(user_message),
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = response.content[0].text
        logger.info("Agent response: tokens_in=%d, tokens_out=%d",
                     response.usage.input_tokens, response.usage.output_tokens)

        # Extract JSON from the response (may be wrapped in markdown code blocks)
        json_text = raw_text.strip()
        if json_text.startswith("```"):
            # Remove markdown code fences
            lines = json_text.split("\n")
            json_text = "\n".join(lines[1:-1])

        parsed = json.loads(json_text)
        return output_type.model_validate(parsed)
