# Contributing to QueryCampus

Welcome to the **QueryCampus** team! This guide explains how our team members collaborate, pick up tasks, build features, and submit Pull Requests.

---

## 👥 Team Roles & Responsibilities

| Contributor | Track & Role | Primary Ownership Areas |
| :--- | :--- | :--- |
| **PARI Javeri** | **RAG & Data Pipeline Engineer** | Document ingestion (`PyPDFDirectoryLoader`), recursive chunking (800c/80o), ChromaDB persistent setup, metadata extraction (`source:page:index`), hybrid search (cosine + BM25 keyword fallback). |
| **Krishna Verma** | **LLM & Backend Integrator** | LLM routing (local Ollama & Groq Cloud API), strict context-injection prompt templates (zero hallucination guardrails), rolling 3-message conversational context memory. |
| **Sachita** | **Full-Stack & UI/UX Developer** | Streamlit web application, responsive concierge UI, inline source citation viewer cards, quick-prompt suggestion chips, model switcher sidebar. |
| **Amannat** | **Integration, Testing & Pitch Lead** | End-to-end latency & accuracy evaluation (`evaluate.py`), Docker & Compose deployment, demo presentation scripts, CI/CD GitHub workflows. |

---

## 🚀 Quick Setup for Contributors

### 1. Clone & Set Up Python Environment
```bash
git clone <repo-url>
cd QueryCampus

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies in editable mode
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

### 2. Configure Environment Variables
Copy the template and adjust if using cloud acceleration:
```bash
cp .env.example .env
```

### 3. Ensure Local Ollama is Running
QueryCampus natively connects to your local Ollama instance:
```bash
# Pull the required embedding and generation models
ollama pull nomic-embed-text
ollama pull orca-mini       # Or gemma3:4b / qwen3.5:4b
```

### 4. Run the Local Development Server
```bash
streamlit run querycampus/ui/app.py
```

---

## 🌿 Git Branching Strategy

To keep collaboration clean and enable concurrent work:
- `main`: Production-ready, verified code. All PRs merge here.
- Feature branches: `feat/<role>-<feature-description>`
  - Example: `feat/pari-hybrid-search`
  - Example: `feat/krishna-groq-fallback`
  - Example: `feat/sachita-citation-cards`
  - Example: `feat/amannat-eval-benchmark`
- Bug fixes: `fix/<short-description>`

---

## 🔄 Development & PR Workflow

1. **Pick an Issue**:
   - Go to the GitHub repository **Issues** tab.
   - Assign yourself an existing task or open a new one using the **Team Task Assignment** template.
2. **Create Branch**:
   ```bash
   git checkout -b feat/<your-name>-<feature>
   ```
3. **Write Tests**:
   - Add unit tests under `tests/` for any new logic.
   - Run tests locally:
     ```bash
     pytest tests/ -v
     ```
4. **Commit & Push**:
   ```bash
   git add .
   git commit -m "feat(pipeline): implement 800c/80o recursive text chunking"
   git push origin feat/<your-name>-<feature>
   ```
5. **Open Pull Request**:
   - Use the prefilled PR template.
   - Link the relevant issue number (`Closes #...`).
   - Request review from your respective teammate.

---

## 🧪 Testing Checklist
Before requesting review on your PR, make sure:
- [ ] All unit tests pass: `pytest tests/`
- [ ] Streamlit interface starts with no errors: `streamlit run querycampus/ui/app.py`
- [ ] End-to-end query retrieves relevant snippets and formats responses without hallucination.
