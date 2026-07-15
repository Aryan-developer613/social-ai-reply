"""Model routing, fallback, and prompt optimization for LLM calls."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.core.config import get_settings
from app.services.infrastructure.llm import providers as _providers_pkg  # noqa: F401 - populates the registry
from app.services.infrastructure.llm.model_aliases import normalize_model_name, parse_provider_list
from app.services.infrastructure.llm.providers._registry import get_configured_providers

if TYPE_CHECKING:
    from app.services.infrastructure.llm.base import LLMProvider

logger = logging.getLogger(__name__)

_PLATFORM_PROMPTS: dict[str, str] = {
    "reddit": (
        "Platform guidance: Write like a helpful community member. Be specific, avoid hype, "
        "and do not push the brand unless the user clearly asked for a solution."
    ),
    "twitter": (
        "Platform guidance: Keep the response concise and conversational. Lead with the point, "
        "avoid long setup, and preserve a human tone."
    ),
    "x": (
        "Platform guidance: Keep the response concise and conversational. Lead with the point, "
        "avoid long setup, and preserve a human tone."
    ),
    "linkedin": (
        "Platform guidance: Be professional, clear, and credibility-focused. Avoid slang and "
        "make the recommendation feel useful rather than promotional."
    ),
    "instagram": (
        "Platform guidance: Use simple, friendly language. Keep the reply short, warm, and easy "
        "to scan on mobile."
    ),
    "hackernews": (
        "Platform guidance: Be precise, technical when useful, and low on marketing language. "
        "Favor evidence, tradeoffs, and practical details."
    ),
    "github": (
        "Platform guidance: Be practical and implementation-focused. Mention concrete fixes, "
        "workflows, or references where relevant."
    ),
    "indiehackers": (
        "Platform guidance: Be founder-friendly and practical. Focus on experiments, customer "
        "learning, and growth tradeoffs."
    ),
}

_MODEL_PROMPTS: dict[str, str] = {
    "claude": "Model guidance: Use natural structure and careful nuance. Keep the output direct.",
    "deepseek": "Model guidance: Favor crisp reasoning and direct conclusions before details.",
    "gemini": "Model guidance: Be concise, grounded, and avoid over-explaining.",
    "glm": "Model guidance: Keep instructions explicit and output formatting simple.",
    "llama": "Model guidance: Use simple, concrete instructions and avoid ornate wording.",
    "ollama": "Model guidance: Use simple, concrete instructions and avoid ornate wording.",
    "openai": "Model guidance: Follow the requested output format strictly.",
    "perplexity": "Model guidance: Prefer factual grounding and mention uncertainty when appropriate.",
    "qwen": "Model guidance: Use direct wording and compact structure.",
}


def _dedupe(items: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _optimization_block(provider_name: str, platform: str | None) -> str:
    blocks: list[str] = []
    platform_key = (platform or "").strip().lower()
    if platform_key in _PLATFORM_PROMPTS:
        blocks.append(_PLATFORM_PROMPTS[platform_key])
    model_prompt = _MODEL_PROMPTS.get(provider_name)
    if model_prompt:
        blocks.append(model_prompt)
    return "\n".join(blocks)


def optimize_messages_for_model(
    messages: list[dict[str, str]],
    provider_name: str,
    platform: str | None = None,
) -> list[dict[str, str]]:
    """Append platform/model guidance to the system message for a provider."""
    optimization = _optimization_block(provider_name, platform)
    if not optimization:
        return [dict(message) for message in messages]

    optimized: list[dict[str, str]] = []
    applied = False
    for message in messages:
        copied = dict(message)
        if copied.get("role") == "system" and not applied:
            copied["content"] = f"{copied.get('content', '').rstrip()}\n\n{optimization}".strip()
            applied = True
        optimized.append(copied)

    if not applied:
        optimized.insert(0, {"role": "system", "content": optimization})

    return optimized


@dataclass(frozen=True)
class LLMRouteResult:
    provider_name: str
    content: str | dict[str, Any] | list[Any]


class LLMRouter:
    """Route LLM calls across configured providers with ordered fallback."""

    def __init__(
        self,
        *,
        primary_provider_name: str | None = None,
        fallback_provider_names: list[str] | None = None,
        providers: dict[str, LLMProvider] | None = None,
        allow_template_fallback: bool = False,
    ) -> None:
        settings = get_settings()
        configured = providers if providers is not None else get_configured_providers()

        if allow_template_fallback and "template" not in configured:
            from app.services.infrastructure.llm.providers.template_provider import TemplateProvider

            configured = {**configured, "template": TemplateProvider()}

        self._providers = configured
        self._primary_provider_name = normalize_model_name(primary_provider_name or settings.llm_provider)
        self._fallback_provider_names = fallback_provider_names or parse_provider_list(settings.llm_fallback_providers)

        if not self._providers:
            raise ValueError("No configured LLM providers are available.")

    @property
    def providers(self) -> dict[str, LLMProvider]:
        return dict(self._providers)

    @property
    def primary_provider(self) -> LLMProvider:
        order = self._provider_order()
        if not order:
            raise ValueError("No configured LLM providers are available for the current route.")
        return self._providers[order[0]]

    def _provider_order(self, model_hint: str | None = None) -> list[str]:
        hinted_provider = normalize_model_name(model_hint)
        configured_order = list(self._providers.keys())
        llama_fallback = "ollama" if hinted_provider == "llama" else None
        requested_order = _dedupe([
            hinted_provider,
            llama_fallback,
            self._primary_provider_name,
            *self._fallback_provider_names,
            *configured_order,
        ])
        return [name for name in requested_order if name in self._providers]

    def call_text(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        model_hint: str | None = None,
        platform: str | None = None,
    ) -> LLMRouteResult | None:
        for provider_name in self._provider_order(model_hint):
            provider = self._providers[provider_name]
            try:
                optimized = optimize_messages_for_model(messages, provider_name, platform)
                result = provider.chat_text(optimized, temperature=temperature, max_tokens=max_tokens)
                if result:
                    return LLMRouteResult(provider_name=provider_name, content=result)
                logger.warning("LLM provider %s returned empty text response.", provider_name)
            except Exception:
                logger.exception("LLM provider %s failed during text generation.", provider_name)
        return None

    def call_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        model_hint: str | None = None,
        platform: str | None = None,
    ) -> LLMRouteResult | None:
        for provider_name in self._provider_order(model_hint):
            provider = self._providers[provider_name]
            try:
                optimized = optimize_messages_for_model(messages, provider_name, platform)
                result = provider.chat_json(optimized, temperature=temperature)
                if result is not None:
                    return LLMRouteResult(provider_name=provider_name, content=result)
                logger.warning("LLM provider %s returned empty JSON response.", provider_name)
            except Exception:
                logger.exception("LLM provider %s failed during JSON generation.", provider_name)
        return None
