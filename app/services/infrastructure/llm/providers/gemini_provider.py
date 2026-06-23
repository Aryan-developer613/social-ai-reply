"""Gemini LLM provider — uses httpx for the Gemini REST API."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import httpx

from app.services.infrastructure.llm._json_helpers import parse_json_payload
from app.services.infrastructure.llm.providers._registry import register

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)

_MAX_RETRIES = 5
_INITIAL_BACKOFF = 4.0


class GeminiProvider:
    """Gemini provider using the native REST API via httpx.

    Gemini's API is not OpenAI-compatible, so we use httpx directly.
    Includes retry with exponential backoff for 429 rate-limit errors.
    """

    def __init__(self, api_key: str, model: str, api_url: str) -> None:
        self._api_key = api_key
        self._model = model
        self._api_url = api_url.rstrip("/")

    @classmethod
    def from_settings(cls, settings: Settings) -> GeminiProvider | None:
        if not settings.gemini_api_key:
            return None
        return cls(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            api_url=settings.gemini_api_url,
        )

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _request_with_retry(self, payload: dict[str, Any]) -> httpx.Response:
        """POST to Gemini with retry on 429."""
        url = f"{self._api_url}/models/{self._model}:generateContent"
        headers = {"x-goog-api-key": self._api_key}

        backoff = _INITIAL_BACKOFF
        for attempt in range(1, _MAX_RETRIES + 1):
            resp = httpx.post(url, json=payload, headers=headers, timeout=60)
            if resp.status_code != 429:
                resp.raise_for_status()
                return resp

            retry_after = resp.headers.get("retry-after")
            if retry_after:
                try:
                    wait = float(retry_after)
                except ValueError:
                    wait = backoff
            else:
                wait = backoff

            logger.warning(
                "Gemini 429 rate-limited (attempt %d/%d), retrying in %.1fs",
                attempt, _MAX_RETRIES, wait,
            )
            time.sleep(wait)
            backoff = min(backoff * 2, 60)

        resp.raise_for_status()
        return resp

    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> dict[str, Any] | list[Any] | None:
        try:
            prompt = self._format_messages(messages)
            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "responseMimeType": "application/json",
                },
            }
            resp = self._request_with_retry(payload)
            data = resp.json()
            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "{}")
            )
            return parse_json_payload(text)
        except Exception:
            logger.exception("Gemini chat_json failed")
            return None

    def chat_text(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str | None:
        try:
            prompt = self._format_messages(messages)
            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
            }
            resp = self._request_with_retry(payload)
            data = resp.json()
            return (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text")
            )
        except Exception:
            logger.exception("Gemini chat_text failed")
            return None

    @staticmethod
    def _format_messages(messages: list[dict[str, str]]) -> str:
        """Format messages into a single prompt string with role labels for Gemini."""
        parts: list[str] = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                parts.append(f"[System Instructions]\n{msg['content']}")
            elif role == "assistant":
                parts.append(f"[Assistant]\n{msg['content']}")
            else:
                parts.append(msg["content"])
        return "\n\n".join(parts)


register("gemini", GeminiProvider)
