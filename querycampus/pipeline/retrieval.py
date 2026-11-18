"""
Hybrid Retrieval Module.
Combines Dense Semantic Cosine Similarity search with Keyword Matching Fallback.
Maintained by: PARI Javeri (RAG & Data Pipeline Engineer)
"""

from typing import List, Dict, Any, Optional, Tuple
import re

from querycampus.config import TOP_K
from querycampus.pipeline.vector_store import ChromaVectorStore


class HybridRetriever:
    """
    Hybrid retriever that blends dense vector cosine similarity
    with BM25 / token-overlap keyword fallback for domain factoid queries.
    """

    def __init__(
        self,
        vector_store: ChromaVectorStore,
        similarity_threshold: float = 0.45,
        keyword_weight: float = 0.3,
    ):
        self.vector_store = vector_store
        self.similarity_threshold = similarity_threshold
        self.keyword_weight = keyword_weight

    def _keyword_score(self, query: str, document: str) -> float:
        """Computes normalized term overlap score between query and document."""
        query_tokens = set(re.findall(r"\w+", query.lower()))
        # Filter stop words
        stop_words = {"the", "is", "at", "which", "on", "a", "an", "and", "or", "in", "for", "to", "of", "what", "where", "how"}
        meaningful_tokens = {t for t in query_tokens if t not in stop_words and len(t) > 2}
        if not meaningful_tokens:
            return 0.0

        doc_lower = document.lower()
        matches = sum(1 for token in meaningful_tokens if token in doc_lower)
        return matches / len(meaningful_tokens)

    def retrieve(
        self,
        query: str,
        top_k: int = TOP_K,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], float, float]:
        """
        Executes hybrid retrieval:
        1. Semantic Cosine Similarity query via Chroma DB.
        2. Applies keyword fallback boost to score chunks.
        Returns: (ranked_hits, query_embed_latency, chroma_retrieval_latency).
        """
        # Fetch up to top_k * 2 candidates from vector store
        candidate_k = max(top_k * 2, 4)
        hits, embed_time, retrieval_time = self.vector_store.query(
            query_text=query,
            top_k=candidate_k,
            where_filter=where_filter,
        )

        if not hits:
            return [], embed_time, retrieval_time

        # Re-score candidates with hybrid weight
        scored_hits = []
        for hit in hits:
            semantic_score = hit.get("similarity", 0.0)
            kw_score = self._keyword_score(query, hit.get("text", ""))

            # Hybrid score formulation
            hybrid_score = (1.0 - self.keyword_weight) * semantic_score + (self.keyword_weight * kw_score)

            hit_copy = dict(hit)
            hit_copy["hybrid_score"] = hybrid_score
            hit_copy["keyword_score"] = kw_score
            scored_hits.append(hit_copy)

        # Sort descending by hybrid_score
        scored_hits.sort(key=lambda x: x["hybrid_score"], reverse=True)
        top_hits = scored_hits[:top_k]

        return top_hits, embed_time, retrieval_time
