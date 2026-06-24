"""Embedding service facade - unified entry point for text embeddings."""

from __future__ import annotations

import hashlib
import logging
import threading
from typing import TYPE_CHECKING

import numpy as np

from app.services.infrastructure.embeddings.providers.tfidf_provider import TfidfProvider

if TYPE_CHECKING:
    from app.services.infrastructure.embeddings.providers.sentence_transformer_provider import (
        SentenceTransformerProvider,
    )

logger = logging.getLogger(__name__)

_DEFAULT_MAX_CACHE_SIZE = 1000


def _normalize_text(text: str) -> str:
    """Normalize text for stable hashing."""
    return " ".join(text.lower().split())


def _text_hash(text: str) -> str:
    """Return a stable hash for the normalized text."""
    return hashlib.md5(_normalize_text(text).encode("utf-8"), usedforsecurity=False).hexdigest()


class EmbeddingService:
    """Singleton-like facade for text embedding and similarity.

    Supports TF-IDF (default) and optional sentence-transformers backends.
    Thread-safe via locks when fitting TF-IDF vectorizer on demand.

    The singleton caches the first instance per ``model_name``. If a subsequent
    construction request a different ``model_name``, the singleton is recreated
    with the new provider (Issue #64). Use ``EmbeddingService.reset()`` to
    explicitly clear the cached instance.
    """

    _instance: EmbeddingService | None = None
    _instance_model_name: str | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, model_name: str = "tfidf", max_cache_size: int = _DEFAULT_MAX_CACHE_SIZE) -> EmbeddingService:
        # Read the class-level model name under the lock so that concurrent
        # calls can't both decide to recreate when a switch is in progress.
        with cls._lock:
            if cls._instance is None:
                # No instance yet — create one and remember the model name
                # BEFORE returning so concurrent threads see a consistent
                # (instance, model_name) pair and don't spuriously recreate.
                inst = super().__new__(cls)
                inst._initialized = False
                cls._instance = inst
                cls._instance_model_name = model_name
                return inst
            if cls._instance_model_name != model_name:
                # Recreate when the requested model differs from the cached one.
                inst = super().__new__(cls)
                inst._initialized = False
                cls._instance = inst
                cls._instance_model_name = model_name
                return inst
            return cls._instance

    def __init__(self, model_name: str = "tfidf", max_cache_size: int = _DEFAULT_MAX_CACHE_SIZE) -> None:
        if self._initialized and getattr(self, "_model_name", None) == model_name:
            return
        with self._lock:
            if self._initialized and getattr(self, "_model_name", None) == model_name:
                return
            self._model_name = model_name
            self._max_cache_size = max_cache_size
            self._cache: dict[str, list[float]] = {}
            self._cache_lock = threading.Lock()
            self._provider = self._create_provider()
            self._initialized = True

    @classmethod
    def reset(cls) -> None:
        """Clear the cached singleton instance (Issue #64).

        The next ``EmbeddingService(...)`` call will recreate it from scratch.
        """
        with cls._lock:
            cls._instance = None
            cls._instance_model_name = None

    def _create_provider(self) -> TfidfProvider | SentenceTransformerProvider:
        name = self._model_name
        if name == "sentence-transformers":
            try:
                from app.services.infrastructure.embeddings.providers.sentence_transformer_provider import (
                    SentenceTransformerProvider,
                )

                logger.info("Using sentence-transformers embedding provider.")
                return SentenceTransformerProvider()
            except Exception as exc:
                logger.warning(
                    "sentence-transformers provider failed to load (%s). Falling back to TF-IDF.",
                    exc,
                )
                return TfidfProvider()
        return TfidfProvider()

    def _get_cached(self, text: str) -> list[float] | None:
        key = _text_hash(text)
        with self._cache_lock:
            return self._cache.get(key)

    def _set_cached(self, text: str, embedding: list[float]) -> None:
        key = _text_hash(text)
        with self._cache_lock:
            if len(self._cache) >= self._max_cache_size:
                # Simple LRU eviction: remove an arbitrary oldest key
                # Python 3.7+ dict preserves insertion order
                self._cache.pop(next(iter(self._cache)), None)
            self._cache[key] = embedding

    def embed_text(self, text: str) -> list[float]:
        """Return embedding vector for a single text (with caching)."""
        cached = self._get_cached(text)
        if cached is not None:
            return cached

        embedding = self._provider.embed(text)
        self._set_cached(text, embedding)
        return embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for a batch of texts (with caching)."""
        results: list[list[float]] = []
        uncached_texts: list[str] = []
        uncached_indices: list[int] = []

        for idx, text in enumerate(texts):
            cached = self._get_cached(text)
            if cached is not None:
                results.append(cached)
            else:
                results.append([])
                uncached_texts.append(text)
                uncached_indices.append(idx)

        if uncached_texts:
            embeddings = self._provider.embed_batch(uncached_texts)
            for idx, text, emb in zip(uncached_indices, uncached_texts, embeddings, strict=False):
                self._set_cached(text, emb)
                results[idx] = emb

        return results

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        arr_a = np.array(a, dtype=np.float64)
        arr_b = np.array(b, dtype=np.float64)
        norm_a = np.linalg.norm(arr_a)
        norm_b = np.linalg.norm(arr_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(arr_a, arr_b) / (norm_a * norm_b))

    def similarity(self, text_a: str, text_b: str) -> float:
        """Convenience: similarity between two texts.

        TF-IDF embeddings are corpus-dependent: vectors from different fits are
        not comparable, so the TF-IDF path computes a pairwise fit instead of
        using the (corpus-independent) embedding cache.
        """
        if isinstance(self._provider, TfidfProvider):
            return self._provider.pairwise_similarity(text_a, text_b)
        emb_a = self.embed_text(text_a)
        emb_b = self.embed_text(text_b)
        return self.cosine_similarity(emb_a, emb_b)
