"""
Script 3: Retrieval Engine & Context Formatting.
Performs top-k semantic search with keyword fallback and fallback confidence checks.
"""

from typing import List, Dict, Any, Optional, Tuple
import re

from src.vector_store import ChromaVectorStore


class CampusRetriever:
    def __init__(
        self,
        vector_store: ChromaVectorStore,
        keyword_weight: float = 0.25,
        confidence_threshold: float = 0.40,
    ):
        self.vector_store = vector_store
        self.keyword_weight = keyword_weight
        self.confidence_threshold = confidence_threshold

    def _keyword_score(self, query: str, document: str) -> float:
        stop_words = {"the", "is", "at", "which", "on", "a", "an", "and", "or", "in", "for", "to", "of", "what", "where", "how"}
        tokens = {t.lower() for t in re.findall(r"\w+", query) if len(t) > 2 and t.lower() not in stop_words}
        if not tokens:
            return 0.0
        doc_lower = document.lower()
        matches = sum(1 for t in tokens if t in doc_lower)
        return matches / len(tokens)

    def retrieve(
        self,
        query: str,
        top_k: int = 2,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], float, float]:
        """
        Executes hybrid retrieval:
        1. Queries vector store for semantic matches.
        2. Scores with keyword token overlap.
        3. Returns top-k ranked documents and timing.
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
            sem_score = c.get("similarity", 0.0)
            kw_score = self._keyword_score(query, c.get("text", ""))
            hybrid_score = ((1.0 - self.keyword_weight) * sem_score) + (self.keyword_weight * kw_score)

            item = dict(c)
            item["hybrid_score"] = hybrid_score
            item["keyword_score"] = kw_score
            scored.append(item)

        scored.sort(key=lambda x: x["hybrid_score"], reverse=True)
        top_hits = scored[:top_k]

        return top_hits, embed_t, ret_t

    def check_confidence(self, hits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Performs fallback confidence check on retrieved context.
        If confidence is low, alerts the system to recommend an administrative ticket escalation.
        """
        if not hits:
            return {
                "is_confident": False,
                "top_score": 0.0,
                "threshold": self.confidence_threshold,
                "reason": "No document chunks retrieved",
            }

        top_similarity = hits[0].get("similarity", 0.0)
        is_confident = top_similarity >= self.confidence_threshold

        return {
            "is_confident": is_confident,
            "top_score": top_similarity,
            "threshold": self.confidence_threshold,
            "reason": "Sufficient semantic alignment" if is_confident else "Low semantic match confidence",
        }

    def format_context(self, hits: List[Dict[str, Any]]) -> str:
        """Formats retrieved chunks with citations for LLM prompt injection."""
        if not hits:
            return "No official records found matching query."

        context_blocks = []
        for i, hit in enumerate(hits, start=1):
            src = hit.get("metadata", {}).get("source", "Campus Document")
            page = hit.get("metadata", {}).get("page", 1)
            text = hit.get("text", "").strip()
            context_blocks.append(f"[Source {i}: {src} | Page {page}]\n{text}")

        return "\n\n".join(context_blocks)
