"""Model/provider alias helpers for LLM routing."""

from __future__ import annotations

_MODEL_ALIASES: dict[str, str] = {
    "anthropic": "claude",
    "claude": "claude",
    "claude-sonnet": "claude",
    "deepseek": "deepseek",
    "deepseek-chat": "deepseek",
    "deepseek-reasoner": "deepseek",
    "gemini": "gemini",
    "glm": "glm",
    "glm-4": "glm",
    "glm-4-flash": "glm",
    "google": "gemini",
    "gpt": "openai",
    "chatgpt": "openai",
    "llama": "llama",
    "llama3": "llama",
    "llama3.1": "llama",
    "local": "ollama",
    "ollama": "ollama",
    "openai": "openai",
    "perplexity": "perplexity",
    "qwen": "qwen",
    "qwen-plus": "qwen",
    "qwen-max": "qwen",
    "sonar": "perplexity",
    "zhipu": "glm",
}


def normalize_model_name(name: str | None) -> str | None:
    """Map model/provider aliases to registered provider names."""
    if not name:
        return None
    normalized = name.strip().lower().replace("_", "-")
    return _MODEL_ALIASES.get(normalized, normalized)


def parse_provider_list(raw: str | None) -> list[str]:
    """Parse a comma-separated provider list into normalized provider names."""
    if not raw:
        return []
    return [name for item in raw.split(",") if (name := normalize_model_name(item))]
