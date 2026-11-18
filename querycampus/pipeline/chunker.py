"""
Recursive Text Chunking and ID Generation Module.
Complies with IEEE GITCON 2025 Paper Sec. III-B & Figure 2:
- Chunk size: 800 characters
- Chunk overlap: 80 characters
- Chunk ID format: source:page:index
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    source: str
    page: int
    chunk_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source": self.source,
            "page": self.page,
            "chunk_index": self.chunk_index,
            "metadata": self.metadata,
        }


class RecursiveTextSplitter:
    """
    Recursively splits text into chunks of specified length with overlap,
    prioritizing paragraph and sentence boundaries.
    """

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 80,
        separators: Optional[List[str]] = None,
    ):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", "; ", ", ", " "]

    def split_text(self, text: str) -> List[str]:
        """Splits raw text into a list of strings respecting chunk_size & overlap."""
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
                    joined_chunk = separator.join(current_doc).strip()
                    if joined_chunk:
                        final_chunks.append(joined_chunk)

                    # Build overlap from the end of current_doc
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
            joined_chunk = separator.join(current_doc).strip()
            if joined_chunk:
                final_chunks.append(joined_chunk)

        # Merge tiny trailing chunks if needed
        merged = []
        for ch in final_chunks:
            if not ch:
                continue
            merged.append(ch)
        return merged

    def create_chunks_for_page(
        self,
        text: str,
        source: str,
        page: int,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        """
        Splits text and assigns chunk ID: source:page:index
        as required by Algorithm 1 and Figure 2.
        """
        raw_chunks = self.split_text(text)
        chunks: List[DocumentChunk] = []

        # Sanitize source name for ID
        safe_source = re.sub(r"[^\w\-.]", "_", source)

        for idx, chunk_text in enumerate(raw_chunks):
            chunk_id = f"{safe_source}:{page}:{idx}"
            meta = {
                "source": source,
                "page": page,
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
