from __future__ import annotations

from typing import Any

from app.services.infrastructure.llm.model_aliases import normalize_model_name
from app.services.infrastructure.llm.router import LLMRouter, optimize_messages_for_model


class FakeProvider:
    def __init__(
        self,
        name: str,
        *,
        text_response: str | None = None,
        json_response: dict[str, Any] | list[Any] | None = None,
        raises: bool = False,
    ) -> None:
        self._name = name
        self.text_response = text_response
        self.json_response = json_response
        self.raises = raises
        self.text_calls: list[list[dict[str, str]]] = []
        self.json_calls: list[list[dict[str, str]]] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_configured(self) -> bool:
        return True

    def chat_text(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str | None:
        del temperature, max_tokens
        self.text_calls.append(messages)
        if self.raises:
            raise RuntimeError(f"{self._name} failed")
        return self.text_response

    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> dict[str, Any] | list[Any] | None:
        del temperature
        self.json_calls.append(messages)
        if self.raises:
            raise RuntimeError(f"{self._name} failed")
        return self.json_response


def test_normalize_model_aliases() -> None:
    assert normalize_model_name("qwen-plus") == "qwen"
    assert normalize_model_name("deepseek-reasoner") == "deepseek"
    assert normalize_model_name("zhipu") == "glm"
    assert normalize_model_name("llama3.1") == "llama"
    assert normalize_model_name("chatgpt") == "openai"


def test_router_routes_to_model_hint_and_optimizes_prompt() -> None:
    qwen = FakeProvider("qwen", text_response="ok")
    router = LLMRouter(
        primary_provider_name="gemini",
        providers={"gemini": FakeProvider("gemini", text_response="wrong"), "qwen": qwen},
    )

    result = router.call_text(
        [{"role": "system", "content": "Base"}, {"role": "user", "content": "Draft"}],
        model_hint="qwen-plus",
        platform="linkedin",
    )

    assert result is not None
    assert result.provider_name == "qwen"
    assert result.content == "ok"
    system_prompt = qwen.text_calls[0][0]["content"]
    assert "professional" in system_prompt
    assert "direct wording" in system_prompt


def test_router_falls_back_when_primary_raises() -> None:
    router = LLMRouter(
        primary_provider_name="gemini",
        fallback_provider_names=["deepseek"],
        providers={
            "gemini": FakeProvider("gemini", raises=True),
            "deepseek": FakeProvider("deepseek", text_response="fallback"),
        },
    )

    result = router.call_text([{"role": "user", "content": "hello"}])

    assert result is not None
    assert result.provider_name == "deepseek"
    assert result.content == "fallback"


def test_router_falls_back_when_primary_returns_none_for_json() -> None:
    router = LLMRouter(
        primary_provider_name="gemini",
        fallback_provider_names=["glm"],
        providers={
            "gemini": FakeProvider("gemini", json_response=None),
            "glm": FakeProvider("glm", json_response={"ok": True}),
        },
    )

    result = router.call_json([{"role": "user", "content": "json"}])

    assert result is not None
    assert result.provider_name == "glm"
    assert result.content == {"ok": True}


def test_llama_hint_uses_ollama_when_remote_llama_is_not_configured() -> None:
    ollama = FakeProvider("ollama", text_response="local")
    router = LLMRouter(primary_provider_name="gemini", providers={"ollama": ollama})

    result = router.call_text([{"role": "user", "content": "hello"}], model_hint="llama")

    assert result is not None
    assert result.provider_name == "ollama"
    assert result.content == "local"


def test_optimize_messages_inserts_system_message_when_missing() -> None:
    optimized = optimize_messages_for_model(
        [{"role": "user", "content": "hello"}],
        provider_name="deepseek",
        platform="reddit",
    )

    assert optimized[0]["role"] == "system"
    assert "community member" in optimized[0]["content"]
    assert "crisp reasoning" in optimized[0]["content"]
