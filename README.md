# QueryCampus

QueryCampus is an open-source, local-first Virtual University Receptionist and Campus Concierge built with Retrieval-Augmented Generation (RAG).

## Architecture & Tech Stack

- **Document Ingestion**: PDF and text document loader with recursive text chunking (800 character chunk size, 80 character overlap).
- **Vector Storage**: Persistent Chroma vector store using cosine similarity metrics.
- **Embeddings**: Nomic text embeddings via local Ollama inference, with an offline deterministic fallback.
- **Generation**: Local LLM routing via Ollama (Gemma, Orca, Qwen) and cloud acceleration via Groq API.
- **Interface**: Interactive Streamlit web UI with inline source citations and real-time latency breakdown.
- **Evaluation**: Benchmark suite for retrieval accuracy, response correctness, and latency metrics.

## Quick Start

### 1. Set Up Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

### 3. Run Web Application

```bash
streamlit run querycampus/ui/app.py
```

### 4. Run Benchmarks & Tests

```bash
# Run test suite
pytest tests/ -v

# Run evaluation benchmark
python -m querycampus.evaluation.benchmark --fast
```

## Docker Deployment

```bash
docker compose up --build
```

## Contributing & Project Structure

- `querycampus/pipeline/`: Ingestion, chunking, embeddings, and vector store.
- `querycampus/llm/`: Prompts, conversation memory, and model routing.
- `querycampus/ui/`: Streamlit dashboard and UI components.
- `querycampus/evaluation/`: Latency and retrieval accuracy benchmarks.
- `data/documents/`: Campus policy documents and guides.
- `tests/`: Automated unit tests.

See [CONTRIBUTING.md](file:///Users/zuri/Hackathons/QueryCampus/CONTRIBUTING.md) for team role assignments, branching guidelines, and development workflows.
