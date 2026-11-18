import pytest
from src.ingest import RecursiveTextSplitter, DocumentChunk, EmbeddingClient

def test_recursive_splitter():
    splitter = RecursiveTextSplitter(chunk_size=800, chunk_overlap=80)
    assert splitter.chunk_size == 800
    assert splitter.chunk_overlap == 80

def test_invalid_overlap():
    with pytest.raises(ValueError):
        RecursiveTextSplitter(chunk_size=400, chunk_overlap=400)

def test_chunk_creation():
    splitter = RecursiveTextSplitter(chunk_size=120, chunk_overlap=20)
    text = "Campus Policy regulations test. " * 10
    chunks = splitter.create_chunks_for_page(text=text, source="rules.pdf", page=1)
    assert len(chunks) > 0
    assert chunks[0].chunk_id == "rules.pdf:1:0"

def test_embedding_client():
    client = EmbeddingClient()
    vec = client.embed_text("university admission")
    assert len(vec) > 0
    assert isinstance(vec[0], float)
