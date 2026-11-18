import tempfile
import pytest
from src.ingest import DocumentChunk
from src.vector_store import ChromaVectorStore

@pytest.fixture
def temp_store():
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = ChromaVectorStore(persist_dir=tmp_dir, collection_name="test_col")
        yield store

def test_add_and_search(temp_store):
    chunk = DocumentChunk(
        chunk_id="handbook.pdf:1:0",
        text="The minimum required attendance is 75% for all courses.",
        source="handbook.pdf",
        page=1,
        chunk_index=0,
        metadata={"source": "handbook.pdf", "page": 1},
    )
    added = temp_store.add_chunks([chunk])
    assert added == 1
    assert temp_store.count() == 1

    hits, emb_t, ret_t = temp_store.search("attendance requirement", top_k=1)
    assert len(hits) == 1
    assert "75%" in hits[0]["text"]
