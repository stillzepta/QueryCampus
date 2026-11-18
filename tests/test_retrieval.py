import tempfile
import pytest
from querycampus.pipeline.chunker import DocumentChunk
from querycampus.pipeline.vector_store import ChromaVectorStore
from querycampus.pipeline.retrieval import HybridRetriever
from querycampus.pipeline.embeddings import DeterministicFallbackEmbeddingProvider

def test_hybrid_retrieval():
    with tempfile.TemporaryDirectory() as tmp_dir:
        fallback_emb = DeterministicFallbackEmbeddingProvider(dimension=64)
        store = ChromaVectorStore(
            persist_dir=tmp_dir,
            collection_name="test_hybrid",
            embedding_provider=fallback_emb,
        )

        chunks = [
            DocumentChunk(
                chunk_id="rules:1:0",
                text="Hostel gate curfew closes at 9:00 PM on weekdays.",
                source="rules.pdf",
                page=1,
                chunk_index=0,
                metadata={"source": "rules.pdf", "page": 1},
            ),
            DocumentChunk(
                chunk_id="sports:1:0",
                text="The swimming pool and badminton arena are open until 8:00 PM.",
                source="sports.pdf",
                page=1,
                chunk_index=0,
                metadata={"source": "sports.pdf", "page": 1},
            ),
        ]
        store.add_chunks(chunks)

        retriever = HybridRetriever(store, keyword_weight=0.3)
        hits, emb_t, ret_t = retriever.retrieve("What is the curfew time for hostel students?", top_k=1)
        assert len(hits) == 1
        assert "curfew" in hits[0]["text"].lower()
        assert "hybrid_score" in hits[0]
