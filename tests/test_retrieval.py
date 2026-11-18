import tempfile
import pytest
from src.ingest import DocumentChunk
from src.vector_store import ChromaVectorStore
from src.retrieval import CampusRetriever

def test_retrieval_and_formatting():
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = ChromaVectorStore(persist_dir=tmp_dir, collection_name="test_retrieval")
        chunk = DocumentChunk(
            chunk_id="facilities.pdf:1:0",
            text="The finance office is located in Block A, Room 102.",
            source="facilities.pdf",
            page=1,
            chunk_index=0,
            metadata={"source": "facilities.pdf", "page": 1},
        )
        store.add_chunks([chunk])

        retriever = CampusRetriever(store)
        hits, emb_t, ret_t = retriever.retrieve("Where is the finance office?", top_k=1)
        assert len(hits) == 1
        assert "Block A, Room 102" in hits[0]["text"]

        context = retriever.format_context(hits)
        assert "[Source 1: facilities.pdf | Page 1]" in context
