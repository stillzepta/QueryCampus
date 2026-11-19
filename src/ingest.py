"""
Script 1: Document Ingestion, Chunking & Embedding Pipeline.
Loads university PDFs from data/sample_docs/, performs recursive character chunking
(800-character chunk size, 80-character overlap), generates embeddings,
and indexes vectors into ChromaDB.
"""

import os
import sys
import glob
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import requests
import numpy as np
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_DOCS_DIR = Path(os.getenv("SAMPLE_DOCS_DIR", BASE_DIR / "data" / "sample_docs"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "80"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    source: str
    page: int
    chunk_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class RecursiveTextSplitter:
    """Recursively splits text into chunks respecting sentence and word boundaries."""

    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", "; ", ", ", " "]

    def split_text(self, text: str) -> List[str]:
        text = text.strip()
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        return self._recursive_split(text, self.separators)

    def _recursive_split(self, text: str, separators: List[str]) -> List[str]:
        final_chunks: List[str] = []
        separator = separators[-1]
        new_separators: List[str] = []

        for i, sep in enumerate(separators):
            if sep == "":
                separator = ""
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1 :]
                break

        splits = text.split(separator) if separator != "" else list(text)
        current_doc: List[str] = []
        total_len = 0

        for s in splits:
            item_len = len(s) + (len(separator) if current_doc else 0)
            if total_len + item_len > self.chunk_size:
                if total_len > 0:
                    joined = separator.join(current_doc).strip()
                    if joined:
                        final_chunks.append(joined)
                    while total_len > self.chunk_overlap and current_doc:
                        removed = current_doc.pop(0)
                        total_len -= len(removed) + len(separator)

                if new_separators and len(s) > self.chunk_size:
                    sub_chunks = self._recursive_split(s, new_separators)
                    final_chunks.extend(sub_chunks)
                    current_doc = []
                    total_len = 0
                    continue

            current_doc.append(s)
            total_len += len(s) + (len(separator) if len(current_doc) > 1 else 0)

        if current_doc:
            joined = separator.join(current_doc).strip()
            if joined:
                final_chunks.append(joined)

        return [c for c in final_chunks if c]

    def create_chunks_for_page(
        self,
        text: str,
        source: str,
        page: int,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        raw_chunks = self.split_text(text)
        chunks: List[DocumentChunk] = []
        safe_source = re.sub(r"[^\w\-.]", "_", source)
        current_section = "General"

        for idx, chunk_text in enumerate(raw_chunks):
            chunk_id = f"{safe_source}:{page}:{idx}"
            # Extract section heading cleanly (e.g. "SECTION 1: ATTENDANCE REQUIREMENTS")
            section_match = re.search(r"(SECTION\s+[0-9A-Z]+(?::\s*[^:\n\.\d]+)?)", chunk_text, re.IGNORECASE)
            if section_match:
                current_section = section_match.group(1).strip()

            meta = {
                "source": source,
                "page": page,
                "section": current_section,
                "chunk_index": idx,
                "char_length": len(chunk_text),
            }
            if extra_metadata:
                meta.update(extra_metadata)


            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    source=source,
                    page=page,
                    chunk_index=idx,
                    metadata=meta,
                )
            )

        return chunks


class EmbeddingClient:
    """Embeddings generator via Ollama nomic-embed-text with deterministic fallback."""

    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_EMBED_MODEL):
        self.base_url = base_url
        self.model = model

    def embed_text(self, text: str) -> List[float]:
        try:
            resp = requests.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": text},
                timeout=10,
            )
            if resp.status_code == 200:
                embs = resp.json().get("embeddings", [])
                if embs:
                    return embs[0]
        except Exception:
            pass

        try:
            resp = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()["embedding"]
        except Exception:
            pass

        # Deterministic normalized hashed fallback
        dim = 384
        vec = np.zeros(dim, dtype=np.float32)
        words = text.lower().split()
        for w in words:
            vec[hash(w) % dim] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            resp = requests.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": texts},
                timeout=30,
            )
            if resp.status_code == 200:
                embs = resp.json().get("embeddings", [])
                if len(embs) == len(texts):
                    return embs
        except Exception:
            pass

        return [self.embed_text(t) for t in texts]


class DocumentIngestor:
    """Loads PDF and text files, cleans text, and splits into chunks."""

    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.splitter = RecursiveTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.embedding_client = EmbeddingClient()

    def load_pdf(self, file_path: str) -> List[DocumentChunk]:
        if PdfReader is None:
            txt_equiv = Path(file_path).with_suffix(".txt")
            if txt_equiv.exists():
                return self.load_text_file(str(txt_equiv))
            return []
        reader = PdfReader(file_path)
        chunks: List[DocumentChunk] = []
        source_name = Path(file_path).name

        for page_idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            cleaned = " ".join(text.split())
            if not cleaned:
                continue

            page_chunks = self.splitter.create_chunks_for_page(
                text=cleaned,
                source=source_name,
                page=page_idx,
                extra_metadata={"file_type": "pdf", "total_pages": len(reader.pages)},
            )
            chunks.extend(page_chunks)

        return chunks

    def load_text_file(self, file_path: str) -> List[DocumentChunk]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        source_name = Path(file_path).name
        cleaned = " ".join(content.split())
        return self.splitter.create_chunks_for_page(
            text=cleaned,
            source=source_name,
            page=1,
            extra_metadata={"file_type": "txt", "total_pages": 1},
        )

    def load_directory(self, dir_path: Optional[str] = None) -> List[DocumentChunk]:
        target_dir = Path(dir_path or SAMPLE_DOCS_DIR)
        if not target_dir.exists():
            os.makedirs(target_dir, exist_ok=True)
            return []

        all_chunks: List[DocumentChunk] = []
        pdf_files = sorted(glob.glob(str(target_dir / "*.pdf")))
        for pdf in pdf_files:
            try:
                all_chunks.extend(self.load_pdf(pdf))
            except Exception as e:
                print(f"[Warning] Error reading {pdf}: {e}")

        if not pdf_files:
            txt_files = sorted(glob.glob(str(target_dir / "*.txt")))
            for txt in txt_files:
                try:
                    all_chunks.extend(self.load_text_file(txt))
                except Exception as e:
                    print(f"[Warning] Error reading {txt}: {e}")

        return all_chunks


def main():
    print(f"Loading documents from {SAMPLE_DOCS_DIR}...")
    ingestor = DocumentIngestor()
    chunks = ingestor.load_directory()
    print(f"Ingested {len(chunks)} chunks.")

    # Import vector_store to index chunks
    from src.vector_store import ChromaVectorStore
    store = ChromaVectorStore()
    store.clear()
    added = store.add_chunks(chunks)
    print(f"Successfully indexed {added} chunks into ChromaDB at {store.persist_dir}.")


if __name__ == "__main__":
    main()
