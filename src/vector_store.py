"""
Script 2: Chroma Vector Database Manager.
Manages persistent ChromaDB connection, vector upsert, and cosine similarity search.
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings

from src.ingest import DocumentChunk, EmbeddingClient


BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIRECTORY", str(BASE_DIR / "chroma_db"))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "campus_documents")


class ChromaVectorStore:
    def __init__(
        self,
        persist_dir: str = CHROMA_PERSIST_DIR,
        collection_name: str = COLLECTION_NAME,
        embedding_client: Optional[EmbeddingClient] = None,
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.embedding_client = embedding_client or EmbeddingClient()

        os.makedirs(self.persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )

        # Use cosine similarity space
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: List[DocumentChunk], batch_size: int = 50) -> int:
        """Upserts document chunks into Chroma DB with embeddings."""
        if not chunks:
            return 0

        total_added = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            ids = [c.chunk_id for c in batch]
            documents = [c.text for c in batch]
            metadatas = [c.metadata for c in batch]

            embeddings = self.embedding_client.embed_batch(documents)

            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
            )
            total_added += len(batch)

        return total_added

    def search(
        self,
        query: str,
        top_k: int = 2,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], float, float]:
        """
        Performs semantic cosine similarity search.
        Returns: (results, embed_latency_sec, retrieval_latency_sec)
        """
        t0 = time.perf_counter()
        query_vec = self.embedding_client.embed_text(query)
        embed_time = time.perf_counter() - t0

        t1 = time.perf_counter()
        query_args: Dict[str, Any] = {
            "query_embeddings": [query_vec],
            "n_results": min(top_k, max(1, self.collection.count())),
            "include": ["documents", "metadatas", "distances"],
        }
        if where_filter:
            query_args["where"] = where_filter

        raw = self.collection.query(**query_args)
        retrieval_time = time.perf_counter() - t1

        hits: List[Dict[str, Any]] = []
        if raw and raw["ids"] and raw["ids"][0]:
            for i in range(len(raw["ids"][0])):
                chunk_id = raw["ids"][0][i]
                doc_text = raw["documents"][0][i]
                meta = raw["metadatas"][0][i]
                dist = raw["distances"][0][i]
                sim = max(0.0, min(1.0, 1.0 - dist))

                hits.append(
                    {
                        "chunk_id": chunk_id,
                        "text": doc_text,
                        "metadata": meta,
                        "distance": dist,
                        "similarity": sim,
                    }
                )

        return hits, embed_time, retrieval_time

    def count(self) -> int:
        return self.collection.count()

    def clear(self) -> None:
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
