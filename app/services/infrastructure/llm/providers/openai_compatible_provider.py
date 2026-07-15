"""OpenAI-compatible model providers for Qwen, DeepSeek, GLM, and Llama.

These providers are optional and only activate when both a base URL and the
needed credentials are configured. They reuse the OpenAI SDK because these
model families commonly expose a `/chat/completions` compatible endpoint.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, ClassVar

import httpx

from app.services.infrastructure.llm._json_helpers import parse_json_payload
from app.services.infrastructure.llm.providers._registry import register
from app.services.infrastructure.llm.providers._retry import retry_http

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)


def _openai_compatible_exc_types() -> tuple[type, ...]:
    """Return OpenAI SDK exception types without making import-time hard requirements."""
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


class _OpenAICompatibleProvider:
    """Base class for OpenAI-compatible provider wrappers."""

    provider_name: ClassVar[str]
    api_key_setting: ClassVar[str]
    base_url_setting: ClassVar[str]
    model_setting: ClassVar[str]
    require_api_key: ClassVar[bool] = True

    def __init__(self, client: Any, model: str) -> None:
        self._client = client
        self._model = model

    @classmethod
    def from_settings(cls, settings: Settings) -> _OpenAICompatibleProvider | None:
        api_key = getattr(settings, cls.api_key_setting)
        base_url = getattr(settings, cls.base_url_setting)
        model = getattr(settings, cls.model_setting)

        if not base_url or not model:
            return None
        if cls.require_api_key and not api_key:
            return None

        from openai import OpenAI

        client = OpenAI(
            api_key=api_key.get_secret_value() if api_key else cls.provider_name,
            base_url=base_url,
            timeout=httpx.Timeout(30.0, connect=10.0),
            max_retries=3,
        )
        return cls(client, model)

    @property
    def name(self) -> str:
        return self.provider_name

    @property
    def is_configured(self) -> bool:
        return self._client is not None and bool(self._model)

    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> dict[str, Any] | list[Any] | None:
        try:
            resp = retry_http(
                lambda: self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=1500,
                ),
                provider_name=self.provider_name,
            )
            text = resp.choices[0].message.content if resp.choices else None
            return parse_json_payload(text) if text else None
        except (httpx.HTTPError, json.JSONDecodeError, ValueError, KeyError, *_openai_compatible_exc_types()) as exc:
            logger.error("%s chat_json failed: %s: %s", self.provider_name, type(exc).__name__, exc)
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
                provider_name=self.provider_name,
            )
            return resp.choices[0].message.content if resp.choices else None
        except (httpx.HTTPError, json.JSONDecodeError, ValueError, KeyError, *_openai_compatible_exc_types()) as exc:
            logger.error("%s chat_text failed: %s: %s", self.provider_name, type(exc).__name__, exc)
            return None


class QwenProvider(_OpenAICompatibleProvider):
    provider_name = "qwen"
    api_key_setting = "qwen_api_key"
    base_url_setting = "qwen_base_url"
    model_setting = "qwen_model"


class DeepSeekProvider(_OpenAICompatibleProvider):
    provider_name = "deepseek"
    api_key_setting = "deepseek_api_key"
    base_url_setting = "deepseek_base_url"
    model_setting = "deepseek_model"


class GLMProvider(_OpenAICompatibleProvider):
    provider_name = "glm"
    api_key_setting = "glm_api_key"
    base_url_setting = "glm_base_url"
    model_setting = "glm_model"


class LlamaProvider(_OpenAICompatibleProvider):
    provider_name = "llama"
    api_key_setting = "llama_api_key"
    base_url_setting = "llama_base_url"
    model_setting = "llama_model"
    require_api_key = False


register("qwen", QwenProvider)
register("deepseek", DeepSeekProvider)
register("glm", GLMProvider)
register("llama", LlamaProvider)
