import pytest
from querycampus.pipeline.chunker import RecursiveTextSplitter, DocumentChunk

def test_recursive_splitter_initialization():
    splitter = RecursiveTextSplitter(chunk_size=800, chunk_overlap=80)
    assert splitter.chunk_size == 800
    assert splitter.chunk_overlap == 80

def test_invalid_overlap():
    with pytest.raises(ValueError):
        RecursiveTextSplitter(chunk_size=500, chunk_overlap=500)

def test_short_text_no_split():
    splitter = RecursiveTextSplitter(chunk_size=800, chunk_overlap=80)
    text = "Short university document snippet."
    chunks = splitter.split_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text

def test_chunk_id_generation():
    splitter = RecursiveTextSplitter(chunk_size=100, chunk_overlap=20)
    long_text = "Word " * 50
    chunks = splitter.create_chunks_for_page(
        text=long_text,
        source="regulations.pdf",
        page=2,
    )
    assert len(chunks) > 1
    for idx, c in enumerate(chunks):
        assert c.chunk_id == f"regulations.pdf:2:{idx}"
        assert c.source == "regulations.pdf"
        assert c.page == 2
        assert c.chunk_index == idx
