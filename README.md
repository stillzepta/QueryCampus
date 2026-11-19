# QueryCampus

> **Virtual University Receptionist & Campus Concierge**  
> A private, low-latency, retrieval-augmented assistant designed to answer campus inquiries using official institutional documents, featuring role-based access control and automated ticket escalation.

---

## 🏗️ Repository Architecture

```
querycampus/
│
├── .github/
│   └── workflows/
│       └── ci.yml                 # Linting and automated build checks
│
├── api/
│   └── index.py                   # Vercel Serverless Python entry point (WSGI app & handler)
│
├── main.py                        # Root Python entry point (WSGI app export)
├── vercel.json                    # Vercel Serverless routing & rewrites configuration
│
├── data/
│   ├── sample_docs/               # Official PDF handbooks, exam guidelines, hostel rules
│   └── db/                        # SQLite storage for tickets and user sessions
│
├── src/
│   ├── __init__.py
│   ├── auth.py                    # Mock institutional login & role-based access control (Student vs. Admin)
│   ├── ingest.py                  # PDF loading, recursive chunking, and nomic-embed-text embedding
│   ├── vector_store.py            # ChromaDB persistence and semantic cosine similarity search
│   ├── retrieval.py               # Top-k context retrieval and fallback confidence checks
│   ├── generator.py               # LLM inference (Groq/Ollama) with strict prompt grounding
│   └── ticketing.py               # Automated ticket generation for lost & found / admin escalations
│
├── frontend/
│   ├── app.py                     # Streamlit Reception Lobby & Kiosk UI
│   ├── reception_kiosk.html       # Standalone HTML5/CSS3 Walk-In Reception Kiosk
│   └── server.py                  # Lightweight REST API & Kiosk Host (Starlette/Uvicorn)
│
├── notebooks/
│   └── rag_experiments.ipynb      # Prototyping chunk sizes and vector retrieval metrics
│
├── .env.example                   # Environment configuration template (API keys, model selection)
├── .gitignore                     # Ignore chroma_db/, venv/, __pycache__/, *.db, .env
├── Dockerfile                     # Containerization for 1-click deployment
├── docker-compose.yml             # Multi-service orchestration (App + Chroma)
├── README.md                      # Project documentation and setup guide
└── requirements.txt               # Python package dependencies
```

---

## 🔑 Key Capabilities

1. **RAG Campus Information Retrieval**:
   - Chunks official university documents with `RecursiveTextSplitter` (800-character chunks, 80-character overlap).
   - Generates high-dimensional embeddings via `nomic-embed-text` with persistent ChromaDB storage and cosine similarity retrieval.
   - Evaluates retrieval confidence with automated low-confidence fallback alerting.

2. **Role-Based Access Control (RBAC)**:
   - **Student Role**: Accesses campus concierge chatbot, quick-prompt chips, inline source citation cards, and personal support ticket submission & tracking.
   - **Administrator Role**: Unlocks the **Admin Dashboard** to review escalated tickets across departments (Lost & Found, Facilities, Fees), manage ticket statuses, and re-index the Chroma knowledge base.

3. **Automated Ticket Escalation**:
   - Detects queries requiring human administrative action (e.g., lost ID cards, hostel maintenance, fee disputes).
   - Backed by persistent SQLite storage (`data/db/campus.db`).

4. **Multi-Model Support**:
   - Fully local, offline inference using Ollama (`gemma3:4b`, `orca-mini`, `qwen3.5:4b`).
   - Cloud acceleration support via Groq API for sub-second responses.

---

## ⚡ Quick Start Guide

### 1. Set Up Environment
```bash
git clone git@github.com:stillzepta/QueryCampus.git
cd QueryCampus

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
```

### 3. Ingest Institutional Documents
```bash
python src/ingest.py
```

### 4. Start the Application

You can launch QueryCampus in either interface mode:

#### Option A: Streamlit Reception UI (Recommended)
```bash
streamlit run frontend/app.py
```
*Features interactive reception lobby, animated Clara front desk, golden desk bell chime, citation cards, and admin dashboard.*

#### Option B: Standalone Interactive Walk-In Kiosk
```bash
python frontend/server.py
```
*Runs on `http://localhost:8000` with fluid CSS walk-in animations, Web Audio synthesized service bell, browser voice synthesis (TTS), department quick trays, and escalation modals. You can also open `frontend/reception_kiosk.html` directly in any web browser!*

### 5. Run Unit Tests
```bash
python tests/run_tests.py
# or if pytest is installed:
pytest tests/ -v
```

---

## 👥 Demo Institutional Credentials

| Role | Email | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Student** (Serina Mehra) | `serina.mehra@bosscoder.edu` | `password123` | Concierge Chat, Citations, Ticket Submission |
| **Administrator** | `admin@pesu.pes.edu` | `adminpassword` | Admin Ticket Dashboard, KB Re-indexing, Full Access |

---

## 🐳 Docker Deployment

```bash
docker compose up --build
```
The application will be live at `http://localhost:8501`.

---

## ▲ Vercel Serverless Deployment

QueryCampus includes native Vercel Python Serverless deployment support:
- **Serverless Entrypoint:** [api/index.py](file:///Users/zuri/Hackathons/QueryCampus/api/index.py) (exposes standard WSGI `app` and HTTP `handler`).
- **Configuration:** [vercel.json](file:///Users/zuri/Hackathons/QueryCampus/vercel.json) routes incoming requests directly to the serverless entry point.
- **Root Entrypoint:** [main.py](file:///Users/zuri/Hackathons/QueryCampus/main.py) provides zero-config compatibility for PaaS hosts.

Deploy with the Vercel CLI or via GitHub:
```bash
# Deploy to preview
vercel

# Deploy to production
vercel --prod
```
When deployed, Vercel serves the responsive Daylight Academic Slate & Emerald web concierge at `/` and all REST API routes at `/api/*`.

