import pytest
from querycampus.pipeline.embeddings import (
    DeterministicFallbackEmbeddingProvider,
    get_embedding_provider,
)

def test_fallback_embedding_provider():
    provider = DeterministicFallbackEmbeddingProvider(dimension=384)
    assert provider.dimension == 384

    vec = provider.embed_query("pes university attendance")
    assert len(vec) == 384
    assert isinstance(vec[0], float)

    batch_vecs = provider.embed_documents(["hello", "world"])
    assert len(batch_vecs) == 2
    assert len(batch_vecs[0]) == 384

def test_get_embedding_provider_factory():
    provider = get_embedding_provider()
    assert provider is not None
    emb = provider.embed_query("test query")
    assert len(emb) > 0
