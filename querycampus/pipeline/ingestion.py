"""
Document Ingestion Pipeline.
Loads university PDFs and text documents, extracts page-by-page text,
and coordinates with RecursiveTextSplitter.
Maintained by: PARI Javeri (RAG & Data Pipeline Engineer)
"""

import os
import glob
from pathlib import Path
from typing import List, Optional
from pypdf import PdfReader

from querycampus.config import CHUNK_SIZE, CHUNK_OVERLAP, DOCUMENTS_DIR
from querycampus.pipeline.chunker import RecursiveTextSplitter, DocumentChunk


class DocumentIngestor:
    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    def load_pdf(self, file_path: str) -> List[DocumentChunk]:
        """Reads a PDF file page by page and chunks it."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        reader = PdfReader(str(path))
        chunks: List[DocumentChunk] = []
        source_name = path.name

        for page_idx, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            # Clean non-standard whitespaces
            cleaned_text = " ".join(page_text.split())
            if not cleaned_text:
                continue

            page_chunks = self.splitter.create_chunks_for_page(
                text=cleaned_text,
                source=source_name,
                page=page_idx,
                extra_metadata={
                    "file_type": "pdf",
                    "file_path": str(path.resolve()),
                    "total_pages": len(reader.pages),
                },
            )
            chunks.extend(page_chunks)

        return chunks

    def load_text_file(self, file_path: str) -> List[DocumentChunk]:
        """Reads a text file and chunks it."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        source_name = path.name
        cleaned_text = " ".join(content.split())
        return self.splitter.create_chunks_for_page(
            text=cleaned_text,
            source=source_name,
            page=1,
            extra_metadata={
                "file_type": "txt",
                "file_path": str(path.resolve()),
                "total_pages": 1,
            },
        )

    def load_directory(self, dir_path: Optional[str] = None) -> List[DocumentChunk]:
        """Loads all supported documents (.pdf, .txt) from a directory."""
        target_dir = Path(dir_path or DOCUMENTS_DIR)
        if not target_dir.exists():
            os.makedirs(target_dir, exist_ok=True)
            return []

        all_chunks: List[DocumentChunk] = []

        # Load PDFs first
        pdf_files = sorted(glob.glob(str(target_dir / "*.pdf")))
        for pdf in pdf_files:
            try:
                chunks = self.load_pdf(pdf)
                all_chunks.extend(chunks)
            except Exception as e:
                print(f"[Warning] Failed to ingest {pdf}: {e}")

        # If no PDFs found, fall back to .txt
        if not pdf_files:
            txt_files = sorted(glob.glob(str(target_dir / "*.txt")))
            for txt in txt_files:
                try:
                    chunks = self.load_text_file(txt)
                    all_chunks.extend(chunks)
                except Exception as e:
                    print(f"[Warning] Failed to ingest {txt}: {e}")

        return all_chunks


def main():
    """CLI Entry point for document ingestion."""
    print(f"Loading documents from {DOCUMENTS_DIR}...")
    ingestor = DocumentIngestor()
    chunks = ingestor.load_directory()
    print(f"Successfully processed {len(chunks)} chunks.")
    for c in chunks[:3]:
        print(f" -> ID: {c.chunk_id} ({len(c.text)} chars): {c.text[:80]}...")


if __name__ == "__main__":
    main()
