"""
Chroma Vector Database Integration Module.
Implements persistent storage with Cosine Similarity metric.
Complies with IEEE GITCON 2025 Paper Sec. III-C & Table I:
- Vector Store: Chroma DB (persistent)
- Similarity Metric: Cosine Similarity ("hnsw:space": "cosine")
- Top-k Retrieval: k=2 (configurable)
- Metadata Tagging: source, page, chunk_index, etc.
Maintained by: PARI Javeri (RAG & Data Pipeline Engineer)
"""

import os
import time
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings

from querycampus.config import (
    CHROMA_PERSIST_DIRECTORY,
    CHROMA_COLLECTION_NAME,
    TOP_K,
)
from querycampus.pipeline.chunker import DocumentChunk
from querycampus.pipeline.embeddings import (
    BaseEmbeddingProvider,
    get_embedding_provider,
)


class ChromaVectorStore:
    def __init__(
        self,
        persist_dir: str = CHROMA_PERSIST_DIRECTORY,
        collection_name: str = CHROMA_COLLECTION_NAME,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.embedding_provider = embedding_provider or get_embedding_provider()

        os.makedirs(self.persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )

        # Cosine distance metric configuration
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: List[DocumentChunk], batch_size: int = 50) -> int:
        """Embeds and indexes document chunks in Chroma DB."""
        if not chunks:
            return 0

        total_added = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            ids = [c.chunk_id for c in batch]
            documents = [c.text for c in batch]
            metadatas = [c.metadata for c in batch]

            embeddings = self.embedding_provider.embed_documents(documents)

            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
            )
            total_added += len(batch)

        return total_added

    def query(
        self,
        query_text: str,
        top_k: int = TOP_K,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], float, float]:
        """
        Executes top-k semantic cosine similarity search.
        Returns (results, query_embed_latency_sec, chroma_retrieval_latency_sec).
        """
        # Step 1: Embed query
        t0 = time.perf_counter()
        query_vec = self.embedding_provider.embed_query(query_text)
        embed_time = time.perf_counter() - t0

        # Step 2: Query Chroma DB
        t1 = time.perf_counter()
        query_kwargs: Dict[str, Any] = {
            "query_embeddings": [query_vec],
            "n_results": min(top_k, max(1, self.collection.count())),
            "include": ["documents", "metadatas", "distances"],
        }
        if where_filter:
            query_kwargs["where"] = where_filter

        raw_results = self.collection.query(**query_kwargs)
        retrieval_time = time.perf_counter() - t1

        hits: List[Dict[str, Any]] = []
        if raw_results and raw_results["ids"] and raw_results["ids"][0]:
            count = len(raw_results["ids"][0])
            for i in range(count):
                chunk_id = raw_results["ids"][0][i]
                doc_text = raw_results["documents"][0][i]
                meta = raw_results["metadatas"][0][i]
                distance = raw_results["distances"][0][i]
                # In Chroma with cosine space, distance = 1 - cosine_similarity
                similarity = max(0.0, min(1.0, 1.0 - distance))

                hits.append(
                    {
                        "chunk_id": chunk_id,
                        "text": doc_text,
                        "metadata": meta,
                        "distance": distance,
                        "similarity": similarity,
                    }
                )

        return hits, embed_time, retrieval_time

    def count(self) -> int:
        return self.collection.count()

    def clear(self) -> None:
        """Deletes all items in the collection."""
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
