"""Small LLM client abstraction used by optional answer composition."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


class LlmClient(Protocol):
    """Minimal text generation interface."""

    def generate(self, messages: list[dict[str, str]], temperature: float = 0.0) -> str:
        """Generate one text response from chat-style messages."""


@dataclass(frozen=True)
class OpenAICompatibleChatClient:
    """Call an OpenAI-compatible chat completions endpoint."""

    api_key: str
    model: str
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: int = 60

    def generate(self, messages: list[dict[str, str]], temperature: float = 0.0) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self.base_url.rstrip('/')}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise LlmGenerationError(str(exc)) from exc

        parsed = json.loads(response_body)
        try:
            content = parsed["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmGenerationError("LLM response did not include message content.") from exc
        if not isinstance(content, str) or not content.strip():
            raise LlmGenerationError("LLM response content was empty.")
        return content.strip()


class LlmGenerationError(RuntimeError):
    """Raised when optional LLM generation fails."""
