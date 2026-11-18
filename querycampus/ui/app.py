"""
QueryCampus: Virtual University Receptionist & Campus Concierge.
Complies with IEEE GITCON 2025 Paper and Hackathon Project Plan:
- Inline Source Card Citations (PDF page, document title, exact snippet)
- Quick-Prompt Suggestion Chips
- Multi-turn Conversational Memory (Rolling 3-Message Window)
- Local Ollama & Cloud LLM Router
- Real-time Latency Breakdown Cards (Embedding, Retrieval, Generation)
Maintained by: Sachita (Full-Stack & UI/UX Developer)
"""

import os
import time
from pathlib import Path
import streamlit as st

from querycampus.config import (
    DOCUMENTS_DIR,
    OLLAMA_LLM_MODEL,
    TOP_K,
    MAX_HISTORY_TURNS,
)
from querycampus.pipeline.ingestion import DocumentIngestor
from querycampus.pipeline.vector_store import ChromaVectorStore
from querycampus.pipeline.retrieval import HybridRetriever
from querycampus.llm.prompts import StrictPromptEngine
from querycampus.llm.memory import ConversationMemory
from querycampus.llm.router import LLMRouter


# Streamlit Page Config
st.set_page_config(
    page_title="QueryCampus - University Concierge",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for polished styling
st.markdown(
    """
    <style>
    /* Main container styling */
    .main-header {
        background: linear-gradient(135deg, #0B3C5D 0%, #1D2731 100%);
        color: white;
        padding: 24px;
        border-radius: 12px;
        margin-bottom: 24px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    .main-header h1 {
        color: #F8F9FA !important;
        font-size: 2.2rem;
        margin-bottom: 4px;
        font-weight: 700;
    }
    .main-header p {
        color: #D9B310;
        font-size: 1.05rem;
        margin: 0;
        font-weight: 500;
    }
    .sub-badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.15);
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        margin-top: 8px;
        color: #E0E0E0;
    }
    
    /* Metrics Row */
    .metric-pill {
        display: inline-flex;
        align-items: center;
        background-color: #F1F5F9;
        border: 1px solid #CBD5E1;
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 0.78rem;
        color: #334155;
        margin-right: 8px;
        margin-top: 6px;
    }
    .metric-pill strong {
        color: #0B3C5D;
        margin-left: 4px;
    }

    /* Citation Card */
    .citation-card {
        border-left: 4px solid #0B3C5D;
        background-color: #F8FAFC;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin: 8px 0;
        border-top: 1px solid #E2E8F0;
        border-right: 1px solid #E2E8F0;
        border-bottom: 1px solid #E2E8F0;
    }
    .citation-header {
        font-weight: 600;
        color: #0B3C5D;
        font-size: 0.85rem;
        margin-bottom: 4px;
        display: flex;
        justify-content: space-between;
    }
    .citation-snippet {
        font-size: 0.82rem;
        color: #475569;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        line-height: 1.4;
    }
    .citation-badge {
        background-color: #E2E8F0;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.72rem;
        color: #1E293B;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_system_components():
    """Initializes persistent vector store, prompt engine, router, and memory."""
    store = ChromaVectorStore()
    # Check if empty, auto-ingest default institutional documents
    if store.count() == 0:
        ingestor = DocumentIngestor()
        chunks = ingestor.load_directory()
        if chunks:
            store.add_chunks(chunks)

    retriever = HybridRetriever(store)
    prompt_engine = StrictPromptEngine()
    router = LLMRouter()
    return store, retriever, prompt_engine, router


store, retriever, prompt_engine, router = get_system_components()

# Session State for Conversation Memory
if "memory" not in st.session_state:
    st.session_state.memory = ConversationMemory(max_turns=MAX_HISTORY_TURNS)

if "chat_display" not in st.session_state:
    st.session_state.chat_display = [
        {
            "role": "assistant",
            "content": "Hello! I am your **QueryCampus Virtual Receptionist** for PES University. I provide private, factually verified information on campus regulations, admissions, fees, hostel rules, exam procedures, and departmental office locations based directly on official university documentation. How may I assist you today?",
            "sources": [],
            "latency": None,
        }
    ]

# Header
st.markdown(
    """
    <div class="main-header">
        <h1>🎓 QueryCampus</h1>
        <p>RAG-Based Virtual University Receptionist & Campus Concierge</p>
        <div class="sub-badge">🔒 100% Private Local Inference &bull; Verified Institutional Sources &bull; IEEE GITCON 2025 Architecture</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar configuration
with st.sidebar:
    st.subheader("⚙️ System Configuration")

    # Model selector
    available_models = router.list_local_models()
    if OLLAMA_LLM_MODEL not in available_models and available_models:
        default_idx = 0
    elif OLLAMA_LLM_MODEL in available_models:
        default_idx = available_models.index(OLLAMA_LLM_MODEL)
    else:
        default_idx = 0

    selected_model = st.selectbox(
        "🧠 LLM Generator",
        options=available_models if available_models else ["gemma3:4b", "orca-mini"],
        index=default_idx,
        help="Selects the generative model hosted locally via Ollama.",
    )

    use_groq = st.checkbox(
        "⚡ Groq Cloud Acceleration",
        value=False,
        help="Routes query to Groq Cloud API for sub-second responses.",
    )

    top_k_val = st.slider(
        "🔍 Top-k Document Retrieval",
        min_value=1,
        max_value=5,
        value=TOP_K,
        help="Number of most relevant chunks passed as context to the LLM.",
    )

    st.markdown("---")
    st.subheader("📁 Knowledge Base Status")
    doc_count = store.count()
    st.metric(label="Indexed Chunks in ChromaDB", value=doc_count)

    # Document Uploader
    st.markdown("#### 📤 Upload New Campus PDF")
    uploaded_file = st.file_uploader("Upload official policy PDF", type=["pdf"])
    if uploaded_file is not None:
        if st.button("Index Uploaded Document"):
            with st.spinner("Processing & embedding document..."):
                save_path = DOCUMENTS_DIR / uploaded_file.name
                os.makedirs(DOCUMENTS_DIR, exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                ingestor = DocumentIngestor()
                new_chunks = ingestor.load_pdf(str(save_path))
                added = store.add_chunks(new_chunks)
                st.success(f"Indexed {added} chunks from {uploaded_file.name}!")
                time.sleep(1)
                st.rerun()

    if st.button("🔄 Re-Index All Documents"):
        with st.spinner("Re-indexing..."):
            store.clear()
            ingestor = DocumentIngestor()
            chunks = ingestor.load_directory()
            store.add_chunks(chunks)
            st.success(f"Re-indexed {store.count()} chunks!")
            st.rerun()

    if st.button("🗑️ Clear Chat History"):
        st.session_state.memory.clear()
        st.session_state.chat_display = [
            {
                "role": "assistant",
                "content": "Conversation history reset. How can I assist you?",
                "sources": [],
                "latency": None,
            }
        ]
        st.rerun()

    st.markdown("---")
    st.caption("QueryCampus v1.0 &bull; PES University &bull; Hackathon Edition")


# Quick-Prompt Suggestion Chips
st.markdown("##### 💡 Suggested Questions:")
col1, col2, col3 = st.columns(3)
quick_query = None

with col1:
    if st.button("📌 Minimum Attendance Requirement", use_container_width=True):
        quick_query = "What is the minimum attendance requirement?"
    if st.button("📚 Central Library Timings", use_container_width=True):
        quick_query = "What are the Central Library operating hours?"

with col2:
    if st.button("📍 Finance Office Location", use_container_width=True):
        quick_query = "Where is the finance office located?"
    if st.button("🚪 Hostel Curfew & Gate Pass", use_container_width=True):
        quick_query = "What are the hostel curfew timings and outstation leave procedures?"

with col3:
    if st.button("📝 Grade Appeals & Revaluation", use_container_width=True):
        quick_query = "What is the procedure and fee for examination answer script revaluation?"
    if st.button("🩺 Emergency Medical Help", use_container_width=True):
        quick_query = "Where is the campus health centre and doctor located?"


# Render Conversation History
for msg in st.session_state.chat_display:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Render Latency Pills if present
        if msg.get("latency"):
            lat = msg["latency"]
            st.markdown(
                f"""
                <div>
                    <span class="metric-pill">⚡ Query Embedding: <strong>{lat['embed']:.3f}s</strong></span>
                    <span class="metric-pill">🔍 Chroma Retrieval: <strong>{lat['retrieval']:.3f}s</strong></span>
                    <span class="metric-pill">🧠 LLM Generation: <strong>{lat['gen']:.3f}s</strong></span>
                    <span class="metric-pill">⏱️ Total Latency: <strong>{lat['total']:.3f}s</strong></span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Render Source Citation Cards
        if msg.get("sources"):
            with st.expander(f"📑 Official Source Citations ({len(msg['sources'])} retrieved chunks)", expanded=False):
                for i, src in enumerate(msg["sources"], start=1):
                    sim = src.get("similarity", 0.0) * 100
                    doc_name = src.get("metadata", {}).get("source", "Document")
                    page = src.get("metadata", {}).get("page", 1)
                    st.markdown(
                        f"""
                        <div class="citation-card">
                            <div class="citation-header">
                                <span>📄 Source {i}: {doc_name} (Page {page})</span>
                                <span class="citation-badge">Cosine Match: {sim:.1f}%</span>
                            </div>
                            <div class="citation-snippet">{src.get("text", "")}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )


# User Chat Input
user_input = st.chat_input("Ask a question about campus policies, locations, deadlines, or rules...")
active_query = quick_query or user_input

if active_query:
    # Append user query to UI
    st.session_state.chat_display.append({"role": "user", "content": active_query})
    with st.chat_message("user"):
        st.markdown(active_query)

    # Process query through RAG pipeline
    with st.chat_message("assistant"):
        with st.spinner("Consulting official institutional records..."):
            t_start = time.perf_counter()

            # 1. Retrieval
            hits, emb_t, ret_t = retriever.retrieve(active_query, top_k=top_k_val)

            # 2. Strict Prompt Formulation with Rolling History
            history_context = st.session_state.memory.get_history_as_context()
            prompt = prompt_engine.build_prompt(
                query=active_query,
                retrieved_hits=hits,
                chat_history_str=history_context,
            )

            # 3. Model Generation
            gen_result = router.generate(
                prompt=prompt,
                model_name=selected_model,
                use_groq=use_groq,
            )

            t_total = time.perf_counter() - t_start

            latency_data = {
                "embed": emb_t,
                "retrieval": ret_t,
                "gen": gen_result.generation_time,
                "total": t_total,
            }

            # Update memory & display
            st.session_state.memory.add_turn(
                user_query=active_query,
                assistant_response=gen_result.text,
                sources=hits,
            )

            st.session_state.chat_display.append(
                {
                    "role": "assistant",
                    "content": gen_result.text,
                    "sources": hits,
                    "latency": latency_data,
                }
            )

            # Render generated response
            st.markdown(gen_result.text)

            # Render Latency Pills
            st.markdown(
                f"""
                <div>
                    <span class="metric-pill">⚡ Query Embedding: <strong>{emb_t:.3f}s</strong></span>
                    <span class="metric-pill">🔍 Chroma Retrieval: <strong>{ret_t:.3f}s</strong></span>
                    <span class="metric-pill">🧠 LLM Generation: <strong>{gen_result.generation_time:.3f}s</strong></span>
                    <span class="metric-pill">⏱️ Total Latency: <strong>{t_total:.3f}s</strong></span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Render Source Cards
            if hits:
                with st.expander(f"📑 Official Source Citations ({len(hits)} retrieved chunks)", expanded=True):
                    for i, src in enumerate(hits, start=1):
                        sim = src.get("similarity", 0.0) * 100
                        doc_name = src.get("metadata", {}).get("source", "Document")
                        page = src.get("metadata", {}).get("page", 1)
                        st.markdown(
                            f"""
                            <div class="citation-card">
                                <div class="citation-header">
                                    <span>📄 Source {i}: {doc_name} (Page {page})</span>
                                    <span class="citation-badge">Cosine Match: {sim:.1f}%</span>
                                </div>
                                <div class="citation-snippet">{src.get("text", "")}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
