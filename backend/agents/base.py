"""Base agent class — shared Grok (xAI) API logic for all agents."""

import os
import json
import logging
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

class BaseAgent:
    """Thin wrapper around the Groq API (OpenAI-compatible) used by all agents."""

    name: str = "base"

    def __init__(self):
        # Read env vars at init time (after dotenv has loaded)
        api_key = os.getenv("XAI_API_KEY", "")
        base_url = os.getenv("XAI_BASE_URL", "https://api.groq.com/openai/v1")
        self.model = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    async def call_claude(
        self,
        system: str,
        user_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        """Send a single-turn message to Grok and return the text response."""
        logger.info("[%s] calling Grok (%d char prompt)", self.name, len(user_prompt))
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = response.choices[0].message.content
        logger.info("[%s] received %d char response", self.name, len(text))
        return text

    async def call_claude_json(
        self,
        system: str,
        user_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.4,
    ) -> dict[str, Any]:
        """Call Grok expecting a JSON response. Parses and returns the dict."""
        raw = await self.call_claude(system, user_prompt, max_tokens, temperature)
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            # Remove opening fence (with optional language tag)
            first_newline = cleaned.index("\n")
            cleaned = cleaned[first_newline + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())
