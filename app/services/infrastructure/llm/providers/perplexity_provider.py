"""Perplexity LLM provider — uses OpenAI SDK with Perplexity base URL."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import httpx

from app.services.infrastructure.llm._json_helpers import parse_json_payload
from app.services.infrastructure.llm.providers._registry import register
from app.services.infrastructure.llm.providers._retry import retry_http

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)

PERPLEXITY_BASE_URL = "https://api.perplexity.ai"


def _perplexity_exc_types() -> tuple[type, ...]:
    """Return OpenAI SDK exception types raised by Perplexity calls.

    Perplexity uses the OpenAI SDK, so its transient API failures come from
    openai.* exception classes. We import lazily so the rest of the file is
    usable when openai isn't installed.
    """
    try:
        from openai import (
            APIConnectionError,
            APITimeoutError,
            AuthenticationError,
            BadRequestError,
            InternalServerError,
            NotFoundError,
            PermissionDeniedError,
            RateLimitError,
        )
    except ImportError:
        return ()
    return (
        APIConnectionError,
        APITimeoutError,
        AuthenticationError,
        BadRequestError,
        InternalServerError,
        NotFoundError,
        PermissionDeniedError,
        RateLimitError,
    )


class PerplexityProvider:
    """Perplexity provider using the OpenAI SDK.

    Perplexity exposes an OpenAI-compatible API, so we reuse the SDK
    with a different base_url.
    """

    def __init__(self, client: Any, model: str) -> None:
        self._client = client
        self._model = model

    @classmethod
    def from_settings(cls, settings: Settings) -> PerplexityProvider | None:
        if not settings.perplexity_api_key:
            return None
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.perplexity_api_key.get_secret_value(),
            base_url=PERPLEXITY_BASE_URL,
            timeout=httpx.Timeout(30.0, connect=10.0),
            max_retries=3,
        )
        return cls(client, settings.perplexity_model)

    @property
    def name(self) -> str:
        return "perplexity"

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> dict[str, Any] | list[Any] | None:
        try:
            # Perplexity does not reliably support response_format,
            # so we request normal text and parse JSON from it.
            resp = retry_http(
                lambda: self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                ),
                provider_name="Perplexity",
            )
            text = resp.choices[0].message.content if resp.choices else None
            return parse_json_payload(text) if text else None
        except (httpx.HTTPError, json.JSONDecodeError, ValueError, KeyError, *_perplexity_exc_types()) as exc:
            logger.error("Perplexity chat_json failed: %s: %s", type(exc).__name__, exc)
            return None

    def chat_text(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str | None:
        try:
            resp = retry_http(
                lambda: self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
                provider_name="Perplexity",
            )
            return resp.choices[0].message.content if resp.choices else None
        except (httpx.HTTPError, json.JSONDecodeError, ValueError, KeyError, *_perplexity_exc_types()) as exc:
            logger.error("Perplexity chat_text failed: %s: %s", type(exc).__name__, exc)
            return None


register("perplexity", PerplexityProvider)
