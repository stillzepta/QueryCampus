"""
Script 1: Retrieval Engine, Hybrid Search & Confidence Scoring.
Module: src/retrieval.py
Author: Krishna Verma (LLM & Backend Integrator)

Connects to persistent ChromaDB ('./chroma_db', collection 'university_docs')
using nomic-embed-text embeddings, performs Top-k semantic search with lightweight
BM25/keyword fallback, normalizes similarity to [0.0, 1.0], and checks confidence.
"""

import os
import sys
import re
import math
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.vector_store import ChromaVectorStore, CHROMA_PERSIST_DIR


# Confidence Threshold for RAG contextual grounding
CONFIDENCE_THRESHOLD: float = 0.55
DEFAULT_COLLECTION_NAME: str = "university_docs"


class CampusRetriever:
    """
    Hybrid retriever combining semantic cosine similarity search via ChromaDB
    and keyword / BM25 term frequency matching for low-confidence fallback.
    """

    def __init__(
        self,
        vector_store: Optional[ChromaVectorStore] = None,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        keyword_weight: float = 0.25,
    ):
        self.vector_store = vector_store or ChromaVectorStore(
            persist_dir=CHROMA_PERSIST_DIR,
            collection_name=DEFAULT_COLLECTION_NAME,
        )
        self.confidence_threshold = confidence_threshold
        self.keyword_weight = keyword_weight

    def _tokenize(self, text: str) -> List[str]:
        """Cleans and extracts meaningful lowercase words."""
        stop_words = {
            "the", "is", "at", "which", "on", "a", "an", "and", "or", "in",
            "for", "to", "of", "what", "where", "how", "can", "i", "do",
            "are", "it", "with", "as", "by", "this", "that", "be", "from",
        }
        tokens = re.findall(r"\b[a-zA-Z0-9_\-\.%]+\b", text.lower())
        return [t for t in tokens if t not in stop_words and len(t) > 1]

    def _bm25_term_score(self, query: str, document: str) -> float:
        """
        Lightweight BM25-inspired term frequency score.
        Rewards exact keyword matches and frequency saturation.
        """
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return 0.0

        doc_tokens = self._tokenize(document)
        if not doc_tokens:
            return 0.0

        doc_len = len(doc_tokens)
        avg_len = 100.0  # approximate standard chunk size in tokens
        k1 = 1.2
        b = 0.75

        # Term frequency in document
        score = 0.0
        doc_token_counts: Dict[str, int] = {}
        for token in doc_tokens:
            doc_token_counts[token] = doc_token_counts.get(token, 0) + 1

        matched_terms = 0
        for q_token in set(query_tokens):
            tf = doc_token_counts.get(q_token, 0)
            if tf > 0:
                matched_terms += 1
                # Standard BM25 term weight
                term_score = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_len / avg_len)))
                score += term_score

        # Normalize score into [0.0, 1.0] range
        normalized_score = min(1.0, score / (len(set(query_tokens)) * 1.5))
        return normalized_score

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], float, float]:
        """
        Executes hybrid retrieval:
        1. Top-k semantic cosine similarity search via ChromaDB.
        2. Blends with BM25 keyword score if semantic similarity is borderline.
        Returns: (ranked_hits, embed_time_sec, retrieval_time_sec)
        """
        candidates, embed_t, ret_t = self.vector_store.search(
            query=query,
            top_k=max(top_k * 2, 4),
            where_filter=where_filter,
        )

        if not candidates:
            return [], embed_t, ret_t

        scored = []
        for c in candidates:
            sem_score = float(c.get("similarity", 0.0))
            kw_score = self._bm25_term_score(query, c.get("text", ""))

            # Hybrid score formulation:
            # If semantic score is already strong (>= 0.75), give semantic search higher weight.
            # If semantic score is lower (< 0.55), keyword fallback provides a boost for exact terminology.
            if sem_score >= 0.75:
                hybrid_score = (0.85 * sem_score) + (0.15 * kw_score)
            else:
                hybrid_score = ((1.0 - self.keyword_weight) * sem_score) + (self.keyword_weight * kw_score)

            # Rulebook Precedence Boost:
            # The Official 2026 Rulebook of Bosscoder School of Technology is the supreme authority.
            # If content in this and other files clashes, this rulebook determines the answer.
            src_str = str(c.get("source") or c.get("metadata", {}).get("source", "")).lower()
            if "bosscoder" in src_str or "rulebook" in src_str:
                hybrid_score += 0.15

            # Ensure normalization to [0.0, 1.0]
            final_score = max(0.0, min(1.0, hybrid_score))

            item = dict(c)
            item["score"] = round(final_score, 4)
            item["semantic_score"] = round(sem_score, 4)
            item["keyword_score"] = round(kw_score, 4)
            scored.append(item)

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k], embed_t, ret_t

    def check_confidence(self, hits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Checks if the top retrieved chunk exceeds CONFIDENCE_THRESHOLD (0.55)."""
        if not hits:
            return {
                "is_confident": False,
                "top_score": 0.0,
                "threshold": self.confidence_threshold,
                "reason": "No document chunks retrieved",
            }

        top_score = float(hits[0].get("score", hits[0].get("similarity", 0.0)))
        is_confident = top_score >= self.confidence_threshold

        return {
            "is_confident": is_confident,
            "top_score": top_score,
            "threshold": self.confidence_threshold,
            "reason": "Sufficient semantic alignment" if is_confident else "Confidence below threshold",
        }

    def format_context(self, hits: List[Dict[str, Any]]) -> str:
        """Formats retrieved chunks with citations for LLM prompt injection."""
        if not hits:
            return "No official records found matching query."

        context_blocks = []
        for i, hit in enumerate(hits, start=1):
            src = hit.get("source") or hit.get("metadata", {}).get("source", "Campus Document")
            page = hit.get("page") or hit.get("metadata", {}).get("page", 1)
            section = hit.get("section") or hit.get("metadata", {}).get("section", "General")
            text = hit.get("text", "").strip()
            context_blocks.append(f"[Source {i}: {src} | Page: {page} | Section: {section}]\n{text}")

        return "\n\n".join(context_blocks)

    def retrieve_context(
        self,
        query: str,
        top_k: int = 3,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes hybrid search and returns a structured dictionary matching the
        backend integration contract:
        {
          "chunks": [{"text": str, "source": str, "page": int, "section": str, "score": float}],
          "max_score": float,
          "is_confident": bool,
          "formatted_context": str
        }
        """
        hits, _, _ = self.retrieve(query=query, top_k=top_k, where_filter=metadata_filter)

        structured_chunks: List[Dict[str, Any]] = []
        for h in hits:
            meta = h.get("metadata", {})
            structured_chunks.append(
                {
                    "text": h.get("text", "").strip(),
                    "source": h.get("source") or meta.get("source", "Unknown Document"),
                    "page": int(h.get("page") or meta.get("page", 1)),
                    "section": str(h.get("section") or meta.get("section", "General")),
                    "score": float(h.get("score", h.get("similarity", 0.0))),
                }
            )

        max_score = float(structured_chunks[0]["score"]) if structured_chunks else 0.0
        is_confident = max_score >= self.confidence_threshold
        formatted_context = self.format_context(structured_chunks)

        return {
            "chunks": structured_chunks,
            "max_score": round(max_score, 4),
            "is_confident": is_confident,
            "formatted_context": formatted_context,
        }


# Global module singleton for direct functional usage
_default_retriever: Optional[CampusRetriever] = None


def get_default_retriever() -> CampusRetriever:
    global _default_retriever
    if _default_retriever is None:
        _default_retriever = CampusRetriever()
    return _default_retriever


def retrieve_context(
    query: str,
    top_k: int = 3,
    metadata_filter: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convenience function matching Krishna's backend contract:
    retrieve_context(query: str, top_k: int = 3, metadata_filter: dict = None) -> dict
    """
    retriever = get_default_retriever()
    return retriever.retrieve_context(query=query, top_k=top_k, metadata_filter=metadata_filter)
