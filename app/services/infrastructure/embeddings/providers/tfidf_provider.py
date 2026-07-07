"""Lightweight local text embedding provider for tests and offline fallback."""

from __future__ import annotations

import math
import re

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9'-]*")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "use",
    "with",
}


class TfidfProvider:
    """Small deterministic bag-of-words embedding provider.

    The production default remains Gemini, but this local provider keeps tests
    and offline development usable without external API calls.
    """

    def __init__(self, dimensions: int = 2048) -> None:
        self.dimensions = dimensions
        self._fitted = False

    def fit(self, texts: list[str]) -> None:
        self._fitted = bool(texts)

    def embed(self, text: str) -> list[float]:
        tokens = self._tokens(text)
        if not tokens:
            return [0.0] * self.dimensions if self._fitted else []

        vector = [0.0] * self.dimensions
        for token in tokens:
            index = self._stable_index(token)
            vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not self._fitted:
            self.fit(texts)
        return [self.embed(text) for text in texts]

    def _tokens(self, text: str) -> list[str]:
        return [token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOPWORDS]

    def _stable_index(self, token: str) -> int:
        return sum((index + 1) * ord(char) for index, char in enumerate(token)) % self.dimensions
