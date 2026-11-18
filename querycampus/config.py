"""
QueryCampus Configuration Module.
Centralizes environment variables and RAG hyperparameters as specified in the
PES University / IEEE GITCON 2025 paper and Hackathon project plan.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("QUERYCAMPUS_DATA_DIR", BASE_DIR / "data"))
DOCUMENTS_DIR = DATA_DIR / "documents"

# Chroma Vector Store
CHROMA_PERSIST_DIRECTORY = os.getenv(
    "CHROMA_PERSIST_DIRECTORY", str(BASE_DIR / "chroma_db")
)
CHROMA_COLLECTION_NAME = os.getenv(
    "CHROMA_COLLECTION_NAME", "querycampus_university_docs"
)

# Text Chunking Settings (Paper Sec. III-B & Table I)
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "80"))

# Retrieval Settings (Paper Sec. III-E & Table I)
TOP_K = int(os.getenv("TOP_K", "2"))
SIMILARITY_METRIC = os.getenv("SIMILARITY_METRIC", "cosine")

# Ollama Engine Settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "gemma3:4b")

# Groq Cloud Acceleration (Optional for sub-second latency)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# Conversational Context Window (Paper Sec. III & Hackathon Plan)
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "3"))

# Streamlit UI Port
STREAMLIT_PORT = int(os.getenv("STREAMLIT_SERVER_PORT", "8501"))
