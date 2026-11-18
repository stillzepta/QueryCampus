# 🗺️ QueryCampus Execution Roadmap & Sprint Milestones

Based on the **RAG-Based Virtual University Receptionist & Campus Concierge** Hackathon Sprint Plan and the **IEEE GITCON 2025** reference paper.

---

## ⏱️ Sprint Schedule & Task Tracker

### Phase 1: Setup & Data Ingestion (Hours 0–6)
*Lead: PARI Javeri (RAG & Data Pipeline Engineer)*
- [x] **Task 1.1**: Curate official PES University institutional documents (fee structures, exam guidelines, hostel policies, campus directory).
- [x] **Task 1.2**: Implement recursive text chunking script (`RecursiveTextSplitter`) with 800-character chunk size and 80-character overlap.
- [x] **Task 1.3**: Configure `nomic-embed-text` embedding integration via Ollama API.
- [x] **Task 1.4**: Initialize persistent Chroma Vector Database with metadata tagging (`document_name`, `page_number`, `chunk_id`).
- [x] **Task 1.5**: Implement hybrid retrieval (dense cosine similarity + keyword BM25 fallback).

### Phase 2: Core Generation & Backend Hookup (Hours 6–18)
*Lead: Krishna Verma (LLM & Backend Integrator)*
- [x] **Task 2.1**: Establish local Ollama inference router (`orca-mini`, `gemma3:4b`, `qwen3.5:4b`).
- [x] **Task 2.2**: Integrate optional high-speed cloud fallback (Groq API) for sub-second responses.
- [x] **Task 2.3**: Engineer strict context-injection prompt templates:
  > `"Answer based only on: {context}\nQuestion: {query}\nAnswer:"`
- [x] **Task 2.4**: Implement rolling 3-message context window conversational session memory.
- [x] **Task 2.5**: Construct zero-hallucination guardrails and disclaimer formatting.

### Phase 3: Frontend Polish & "Winning" Features (Hours 18–30)
*Lead: Sachita (Full-Stack & UI/UX Developer)*
- [x] **Task 3.1**: Build modern Streamlit concierge dashboard with custom university styling.
- [x] **Task 3.2**: Build interactive **Inline Source Citation Viewer** cards displaying exact PDF pages and snippet text.
- [x] **Task 3.3**: Implement Quick-Prompt suggestion chips for standard university inquiries (attendance, finance office, grading, hostel).
- [x] **Task 3.4**: Add sidebar controls for model selection, similarity thresholds, and real-time PDF drag-and-drop indexing.
- [x] **Task 3.5**: Display latency breakdown metric cards (Embedding time, Retrieval time, LLM Generation time).

### Phase 4: Testing, Containerization & Pitch (Hours 30–36)
*Lead: Amannat (Integration, Testing & Pitch Lead)*
- [x] **Task 4.1**: Build automated evaluation test runner (`querycampus/evaluation/benchmark.py`) for 50 representative student queries.
- [x] **Task 4.2**: Measure latency metrics matching Table III (Query Embedding: 0.7s, Chroma Retrieval: 0.3s, LLM Gen: ~10.1s on CPU).
- [x] **Task 4.3**: Measure Top-2 retrieval accuracy and response correctness (benchmark target: >90%).
- [x] **Task 4.4**: Package repository with Docker & Docker Compose for reliable 1-click judging evaluation.
- [x] **Task 4.5**: Rehearse 3-minute live pitch script focusing on institutional data privacy, offline edge deployment, and verifiable citation cards.

---

## 📊 Evaluation & Verification Targets (from IEEE GITCON 2025 Paper)

| Metric | Target / Paper Result | QueryCampus Benchmark |
| :--- | :--- | :--- |
| **Embedding Model** | `nomic-embed-text` | Native Ollama (`/api/embeddings`) |
| **LLM Generator** | `orca-mini` (3B) / `gemma3:4b` | Ollama local / Groq cloud |
| **Vector Store** | Chroma DB (persistent) | Chroma with cosine similarity |
| **Chunk Size / Overlap** | 800 chars / 80 chars | Exact 800c / 80o recursive split |
| **Top-k Retrieval** | k = 2 | Configurable (default k=2) |
| **Top-2 Retrieval Accuracy** | 92.0% | Benchmarked on 50 campus queries |
| **Response Correctness** | 88.0% | Context-grounded generation |
| **Failure Rate** | 8.0% | Handled via keyword fallback & query clarification |
| **End-to-End Latency** | 11.1s (CPU) / <1.5s (Cloud) | Live metric timers in UI |
