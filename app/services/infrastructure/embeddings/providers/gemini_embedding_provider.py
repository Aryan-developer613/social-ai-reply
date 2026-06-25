"""Gemini API embedding provider using httpx."""

import logging
import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

class GeminiEmbeddingProvider:
    """Uses Google's Gemini API for generating text embeddings via REST."""

    def __init__(self, model_name: str = "models/gemini-embedding-001") -> None:
        self.model_name = model_name
        self.api_key = get_settings().gemini_api_key
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set. Embeddings will return empty vectors.")
        
        # https://ai.google.dev/api/rest/v1beta/models/embedContent
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/{self.model_name}:embedContent"
        # https://ai.google.dev/api/rest/v1beta/models/batchEmbedContents
        self.batch_api_url = f"https://generativelanguage.googleapis.com/v1beta/{self.model_name}:batchEmbedContents"

    def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        if not self.api_key or not text.strip():
            return []
            
        text = text[:10000]
        
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{self.api_url}?key={self.api_key}",
                    json={
                        "model": self.model_name,
                        "content": {
                            "parts": [{"text": text}]
                        }
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("embedding", {}).get("values", [])
        except Exception as e:
            logger.error("Gemini embedding failed: %s", e)
            return []

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of strings."""
        if not self.api_key or not texts:
            return [[] for _ in texts]
            
        try:
            requests = []
            for text in texts:
                requests.append({
                    "model": self.model_name,
                    "content": {
                        "parts": [{"text": text[:10000]}]
                    }
                })
            
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    f"{self.batch_api_url}?key={self.api_key}",
                    json={"requests": requests}
                )
                resp.raise_for_status()
                data = resp.json()
                embeddings = data.get("embeddings", [])
                
                if len(embeddings) == len(texts):
                    return [emb.get("values", []) for emb in embeddings]
                
                logger.error("Gemini batch embed returned %d embeddings for %d texts", len(embeddings), len(texts))
                return [[] for _ in texts]
                    
        except Exception as e:
            logger.error("Gemini batch embedding failed: %s", e)
            return [[] for _ in texts]
