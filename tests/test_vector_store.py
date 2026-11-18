import tempfile
import pytest
from querycampus.pipeline.chunker import DocumentChunk
from querycampus.pipeline.vector_store import ChromaVectorStore
from querycampus.pipeline.embeddings import DeterministicFallbackEmbeddingProvider

@pytest.fixture
def temp_store():
    with tempfile.TemporaryDirectory() as tmp_dir:
        fallback_emb = DeterministicFallbackEmbeddingProvider(dimension=64)
        store = ChromaVectorStore(
            persist_dir=tmp_dir,
            collection_name="test_collection",
            embedding_provider=fallback_emb,
        )
        yield store

def test_vector_store_add_and_query(temp_store):
    chunks = [
        DocumentChunk(
            chunk_id="doc1:1:0",
            text="The minimum attendance requirement at the university is 75 percent.",
            source="doc1.pdf",
            page=1,
            chunk_index=0,
            metadata={"source": "doc1.pdf", "page": 1},
        ),
        DocumentChunk(
            chunk_id="doc2:1:0",
            text="The finance office is located in Block A Room 102.",
            source="doc2.pdf",
            page=1,
            chunk_index=0,
            metadata={"source": "doc2.pdf", "page": 1},
        ),
    ]

    added = temp_store.add_chunks(chunks)
    assert added == 2
    assert temp_store.count() == 2

    hits, emb_t, ret_t = temp_store.query("attendance requirement", top_k=1)
    assert len(hits) == 1
    assert "attendance" in hits[0]["text"].lower()
    assert emb_t >= 0.0
    assert ret_t >= 0.0
