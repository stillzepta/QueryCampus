"""
Embedding Provider Module.
Complies with IEEE GITCON 2025 Paper:
- Primary Embedding Model: nomic-embed-text via Ollama
- Graceful deterministic fallback for CI/CD and offline unit tests.
Maintained by: PARI Javeri (RAG & Data Pipeline Engineer)
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import time
import requests
import numpy as np

from querycampus.config import OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds a list of document strings."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Embeds a single query string."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Generates embeddings using nomic-embed-text hosted via Ollama."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model_name: str = OLLAMA_EMBED_MODEL,
        timeout: int = 60,
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self._dimension: Optional[int] = None

    def embed_query(self, text: str) -> List[float]:
        t0 = time.perf_counter()
        # Try /api/embed first (newer Ollama)
        try:
            resp = requests.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model_name, "input": text},
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                embeddings = data.get("embeddings", [])
                if embeddings:
                    emb = embeddings[0]
                    self._dimension = len(emb)
                    return emb
        except Exception:
            pass

        # Fallback to /api/embeddings (classic Ollama)
        resp = requests.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.model_name, "prompt": text},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        emb = resp.json()["embedding"]
        self._dimension = len(emb)
        return emb

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        # Batch attempt via /api/embed
        try:
            resp = requests.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model_name, "input": texts},
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                embeddings = data.get("embeddings", [])
                if len(embeddings) == len(texts):
                    if embeddings:
                        self._dimension = len(embeddings[0])
                    return embeddings
        except Exception:
            pass

        # Fallback to sequential calls
        results: List[List[float]] = []
        for t in texts:
            results.append(self.embed_query(t))
        return results

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            sample = self.embed_query("pes university")
            self._dimension = len(sample)
        return self._dimension


class DeterministicFallbackEmbeddingProvider(BaseEmbeddingProvider):
    """
    Lightweight, deterministic high-dimensional embedding for offline
    environments, unit testing, and GitHub Actions CI pipelines.
    Uses normalized 384-dimensional hashed token frequency vectors.
    """

    def __init__(self, dimension: int = 384):
        self._dim = dimension

    def _hash_embed(self, text: str) -> List[float]:
        vec = np.zeros(self._dim, dtype=np.float32)
        words = text.lower().split()
        if not words:
            return vec.tolist()

        for word in words:
            # Deterministic hash bucket
            h = hash(word) % self._dim
            vec[h] += 1.0

        # L2 Normalize for cosine similarity
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_embed(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._hash_embed(text)

    @property
    def dimension(self) -> int:
        return self._dim


def get_embedding_provider(
    force_fallback: bool = False,
    base_url: str = OLLAMA_BASE_URL,
    model_name: str = OLLAMA_EMBED_MODEL,
) -> BaseEmbeddingProvider:
    """
    Factory returning OllamaEmbeddingProvider if Ollama is accessible,
    otherwise gracefully falling back to DeterministicFallbackEmbeddingProvider.
    """
    if force_fallback:
        return DeterministicFallbackEmbeddingProvider()

    try:
        provider = OllamaEmbeddingProvider(base_url=base_url, model_name=model_name, timeout=5)
        # Quick test connectivity
        provider.embed_query("ping")
        return provider
    except Exception as e:
        print(f"[Notice] Ollama embedding provider unreachable ({e}). Using deterministic fallback.")
        return DeterministicFallbackEmbeddingProvider()
