"""
Script 2: Chroma Vector Database Manager.
Manages persistent ChromaDB connection, vector upsert, and cosine similarity search.
"""

import os
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    chromadb = None

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
        self.use_chroma = HAS_CHROMADB
        self._fallback_file = Path(self.persist_dir) / f"{self.collection_name}_fallback.json"
        self._fallback_data: List[Dict[str, Any]] = []

        os.makedirs(self.persist_dir, exist_ok=True)
        if self.use_chroma:
            try:
                self.client = chromadb.PersistentClient(
                    path=self.persist_dir,
                    settings=Settings(anonymized_telemetry=False),
                )
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as e:
                print(f"[VectorStore] ChromaDB init error ({e}), switching to JSON fallback.")
                self.use_chroma = False

        if not self.use_chroma:
            self._load_fallback()

    def _load_fallback(self):
        if self._fallback_file.exists():
            try:
                with open(self._fallback_file, "r", encoding="utf-8") as f:
                    self._fallback_data = json.load(f)
            except Exception:
                self._fallback_data = []
        else:
            self._fallback_data = []

    def _save_fallback(self):
        with open(self._fallback_file, "w", encoding="utf-8") as f:
            json.dump(self._fallback_data, f)

    def add_chunks(self, chunks: List[DocumentChunk], batch_size: int = 50) -> int:
        """Upserts document chunks into Chroma DB or fallback store with embeddings."""
        if not chunks:
            return 0

        total_added = 0
        if self.use_chroma:
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

        # Fallback in-memory/JSON store
        for chunk in chunks:
            emb = self.embedding_client.embed_text(chunk.text)
            existing_idx = next((i for i, d in enumerate(self._fallback_data) if d["id"] == chunk.chunk_id), None)
            item = {
                "id": chunk.chunk_id,
                "text": chunk.text,
                "metadata": chunk.metadata,
                "embedding": emb,
            }
            if existing_idx is not None:
                self._fallback_data[existing_idx] = item
            else:
                self._fallback_data.append(item)
            total_added += 1

        self._save_fallback()
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

        if self.use_chroma:
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

        # Fallback cosine search
        if not self._fallback_data:
            return [], embed_time, time.perf_counter() - t1

        q_arr = np.array(query_vec, dtype=np.float32)
        q_norm = np.linalg.norm(q_arr)
        if q_norm > 0:
            q_arr = q_arr / q_norm

        scored = []
        for item in self._fallback_data:
            if where_filter:
                skip = False
                for k, v in where_filter.items():
                    if item.get("metadata", {}).get(k) != v:
                        skip = True
                        break
                if skip:
                    continue

            d_arr = np.array(item["embedding"], dtype=np.float32)
            d_norm = np.linalg.norm(d_arr)
            if d_norm > 0:
                d_arr = d_arr / d_norm
            sim = float(np.dot(q_arr, d_arr))
            sim = max(0.0, min(1.0, sim))
            dist = 1.0 - sim
            scored.append((sim, dist, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_items = scored[:top_k]
        retrieval_time = time.perf_counter() - t1

        hits = [
            {
                "chunk_id": item["id"],
                "text": item["text"],
                "metadata": item["metadata"],
                "distance": dist,
                "similarity": sim,
            }
            for sim, dist, item in top_items
        ]
        return hits, embed_time, retrieval_time

    def count(self) -> int:
        if self.use_chroma:
            return self.collection.count()
        return len(self._fallback_data)

    def clear(self) -> None:
        if self.use_chroma:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        else:
            self._fallback_data = []
            if self._fallback_file.exists():
                self._fallback_file.unlink()
