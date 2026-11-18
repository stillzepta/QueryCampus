# QueryCampus

> **Virtual University Receptionist & Campus Concierge**  
> A private, low-latency, retrieval-augmented assistant designed to answer campus inquiries using official institutional documents.

---

## 🏗️ Repository Architecture

```
querycampus/
│
├── .github/
│   └── workflows/
│       └── ci.yml             # Automated CI: linting & pytest test checks
│
├── data/
│   └── sample_docs/           # Test documents (handbooks, exam rules, timetables)
│
├── src/
│   ├── __init__.py
│   ├── ingest.py              # Script 1: PDF loading, chunking (RecursiveTextSplitter), & embedding
│   ├── vector_store.py        # Script 2: ChromaDB connection, vector upsert, and search logic
│   ├── retrieval.py           # Script 3: Top-k semantic search & context formatting
│   └── generator.py           # Script 4: LLM integration (Ollama / Groq API) & strict prompting
│
├── frontend/
│   └── app.py                 # Streamlit UI dashboard (chat interface + citation view cards)
│
├── notebooks/                 # Rapid prototyping / testing chunk sizes & embeddings
│   └── rag_experiments.ipynb
│
├── .env.example               # Environment variables template
├── .gitignore                 # Ignores chroma_db/, venv/, __pycache__/, .env
├── Dockerfile                 # Containerization file for 1-click deployment
├── docker-compose.yml         # Multi-container orchestration (App + Chroma/Ollama services)
├── README.md                  # Project overview, setup guide, and team credentials
└── requirements.txt           # Python dependencies
```

---

## 👥 Team Roles & Responsibilities

| Contributor | Track & Role | Core Responsibilities |
| :--- | :--- | :--- |
| **PARI Javeri** | **RAG & Data Pipeline Engineer** | Automated document ingestion, `RecursiveTextSplitter` chunking, ChromaDB vector store, and hybrid retrieval. |
| **Krishna Verma** | **LLM & Backend Integrator** | Model integration (Ollama / Groq API routing), strict context-injection prompt templates, and rolling 3-message session memory. |
| **Sachita** | **Full-Stack & UI/UX Developer** | Streamlit concierge UI, interactive citation cards displaying source pages/snippets, and quick-prompt suggestion chips. |
| **Amannat** | **Integration, Testing & Pitch Lead** | End-to-end latency & accuracy benchmarking, Docker containerization, and demonstration pitch. |

---

## ⚡ Quick Start Guide

### 1. Clone & Set Up Virtual Environment
```bash
git clone git@github.com:stillzepta/QueryCampus.git
cd QueryCampus

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
```

### 3. Ingest Documents into Vector Store
```bash
python src/ingest.py
```

### 4. Start the Web Concierge Dashboard
```bash
streamlit run frontend/app.py
```

### 5. Run Test Suite
```bash
pytest tests/ -v
```

---

## 🐳 Docker Deployment

To launch the full stack with 1 click:
```bash
docker compose up --build
```
The Streamlit application will be accessible at `http://localhost:8501`.

---

## 🔬 Prototyping Notebooks
Open `notebooks/rag_experiments.ipynb` in VS Code or Jupyter Lab to experiment with chunk sizes, token overlaps, and embedding distances.
