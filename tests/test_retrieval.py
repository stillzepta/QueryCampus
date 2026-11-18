import tempfile
import pytest
from src.ingest import DocumentChunk
from src.vector_store import ChromaVectorStore
from src.retrieval import CampusRetriever, retrieve_context

def test_retrieval_and_formatting():
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = ChromaVectorStore(persist_dir=tmp_dir, collection_name="test_retrieval")
        chunk = DocumentChunk(
            chunk_id="facilities.pdf:1:0",
            text="The finance office is located in Block A, Room 102.",
            source="facilities.pdf",
            page=1,
            chunk_index=0,
            metadata={"source": "facilities.pdf", "page": 1, "section": "Admin Offices"},
        )
        store.add_chunks([chunk])

        retriever = CampusRetriever(store, confidence_threshold=0.55)
        res = retriever.retrieve_context("Where is the finance office located?", top_k=1)
        assert len(res["chunks"]) == 1
        assert res["chunks"][0]["source"] == "facilities.pdf"
        assert res["chunks"][0]["section"] == "Admin Offices"
        assert res["chunks"][0]["page"] == 1
        assert "Block A, Room 102" in res["chunks"][0]["text"]
        assert res["is_confident"] is True
        assert res["max_score"] >= 0.55
        assert "[Source 1: facilities.pdf | Page: 1 | Section: Admin Offices]" in res["formatted_context"]

def test_low_confidence_check():
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = ChromaVectorStore(persist_dir=tmp_dir, collection_name="test_empty")
        retriever = CampusRetriever(store, confidence_threshold=0.55)
        res = retriever.retrieve_context("Random unindexed text", top_k=2)
        assert res["is_confident"] is False
        assert res["max_score"] == 0.0
        assert len(res["chunks"]) == 0
