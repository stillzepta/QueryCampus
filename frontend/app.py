"""
QueryCampus: Virtual University Receptionist & Campus Concierge.
Streamlit UI dashboard featuring interactive chat, inline source citation view cards,
quick-prompt chips, and local/cloud LLM routing.
"""

import os
import time
from pathlib import Path
import streamlit as st

from src.ingest import DocumentIngestor, SAMPLE_DOCS_DIR
from src.vector_store import ChromaVectorStore
from src.retrieval import CampusRetriever
from src.generator import CampusGenerator, ConversationMemory


st.set_page_config(
    page_title="QueryCampus - University Concierge",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern styling and citation cards
st.markdown(
    """
    <style>
    .main-header {
        background: linear-gradient(135deg, #0B3C5D 0%, #1D2731 100%);
        color: white;
        padding: 22px 26px;
        border-radius: 12px;
        margin-bottom: 24px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.08);
    }
    .main-header h1 {
        color: #F8F9FA !important;
        font-size: 2.1rem;
        margin-bottom: 4px;
        font-weight: 700;
    }
    .main-header p {
        color: #D9B310;
        font-size: 1.05rem;
        margin: 0;
        font-weight: 500;
    }
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
    .citation-badge {
        background-color: #E2E8F0;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.72rem;
        color: #1E293B;
    }
    .metric-pill {
        display: inline-flex;
        align-items: center;
        background-color: #F1F5F9;
        border: 1px solid #CBD5E1;
        border-radius: 6px;
        padding: 3px 8px;
        font-size: 0.78rem;
        color: #334155;
        margin-right: 8px;
        margin-top: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def init_system():
    store = ChromaVectorStore()
    if store.count() == 0:
        ingestor = DocumentIngestor()
        chunks = ingestor.load_directory()
        if chunks:
            store.add_chunks(chunks)
    retriever = CampusRetriever(store)
    generator = CampusGenerator()
    return store, retriever, generator


store, retriever, generator = init_system()

if "memory" not in st.session_state:
    st.session_state.memory = ConversationMemory(max_turns=3)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! I am **QueryCampus**, your official Virtual University Concierge. Ask me anything about course regulations, office locations, fees, hostel curfew, or campus facilities.",
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
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    st.subheader("⚙️ System Control")
    models = generator.list_available_models()
    selected_model = st.selectbox("🧠 Generative Model", options=models, index=0)
    use_groq = st.checkbox("⚡ Cloud Groq Acceleration", value=False)
    top_k = st.slider("🔍 Top-k Document Retrieval", min_value=1, max_value=5, value=2)

    st.markdown("---")
    st.subheader("📁 Knowledge Base")
    st.metric("Total Indexed Chunks", store.count())

    uploaded_pdf = st.file_uploader("Upload new campus PDF", type=["pdf"])
    if uploaded_pdf and st.button("Index Document"):
        with st.spinner("Processing PDF..."):
            save_path = SAMPLE_DOCS_DIR / uploaded_pdf.name
            os.makedirs(SAMPLE_DOCS_DIR, exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(uploaded_pdf.getbuffer())
            ingestor = DocumentIngestor()
            new_chunks = ingestor.load_pdf(str(save_path))
            added = store.add_chunks(new_chunks)
            st.success(f"Indexed {added} new chunks!")
            time.sleep(1)
            st.rerun()

    if st.button("🔄 Re-Index Knowledge Base"):
        with st.spinner("Re-indexing..."):
            store.clear()
            ingestor = DocumentIngestor()
            chunks = ingestor.load_directory()
            store.add_chunks(chunks)
            st.success(f"Re-indexed {store.count()} chunks!")
            st.rerun()

    if st.button("🗑️ Reset Chat"):
        st.session_state.memory.clear()
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Chat history cleared. How can I help you?",
                "sources": [],
                "latency": None,
            }
        ]
        st.rerun()


# Quick Prompt Chips
st.markdown("##### 💡 Quick Suggestions:")
c1, c2, c3 = st.columns(3)
quick_query = None

with c1:
    if st.button("📌 Minimum Attendance Requirement", use_container_width=True):
        quick_query = "What is the minimum attendance requirement?"
    if st.button("📚 Central Library Timings", use_container_width=True):
        quick_query = "What are the Central Library operating hours?"

with c2:
    if st.button("📍 Finance Office Location", use_container_width=True):
        quick_query = "Where is the finance office located?"
    if st.button("🚪 Hostel Curfew Timings", use_container_width=True):
        quick_query = "What are the hostel curfew timings?"

with c3:
    if st.button("📝 Grade Appeals & Revaluation", use_container_width=True):
        quick_query = "What is the fee and procedure for grade revaluation?"
    if st.button("🩺 Emergency Medical Help", use_container_width=True):
        quick_query = "Where is the campus health centre located?"


# Display chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg.get("latency"):
            lat = msg["latency"]
            st.markdown(
                f"""
                <div>
                    <span class="metric-pill">⚡ Embed: <strong>{lat['embed']:.3f}s</strong></span>
                    <span class="metric-pill">🔍 Retrieve: <strong>{lat['retrieval']:.3f}s</strong></span>
                    <span class="metric-pill">🧠 Gen: <strong>{lat['gen']:.3f}s</strong></span>
                    <span class="metric-pill">⏱️ Total: <strong>{lat['total']:.3f}s</strong></span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if msg.get("sources"):
            with st.expander(f"📑 Citation Cards ({len(msg['sources'])} sources)", expanded=False):
                for i, src in enumerate(msg["sources"], start=1):
                    sim = src.get("similarity", 0.0) * 100
                    doc_name = src.get("metadata", {}).get("source", "Campus Doc")
                    page = src.get("metadata", {}).get("page", 1)
                    st.markdown(
                        f"""
                        <div class="citation-card">
                            <div class="citation-header">
                                <span>📄 Source {i}: {doc_name} (Page {page})</span>
                                <span class="citation-badge">Cosine Match: {sim:.1f}%</span>
                            </div>
                            <div style="font-size:0.82rem; color:#475569;">{src.get("text", "")}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

user_query = st.chat_input("Type your university inquiry here...")
active_query = quick_query or user_query

if active_query:
    st.session_state.messages.append({"role": "user", "content": active_query})
    with st.chat_message("user"):
        st.markdown(active_query)

    with st.chat_message("assistant"):
        with st.spinner("Searching official institutional documents..."):
            t_start = time.perf_counter()
            hits, emb_t, ret_t = retriever.retrieve(active_query, top_k=top_k)
            context = retriever.format_context(hits)
            history_text = st.session_state.memory.get_history_text()

            res = generator.generate(
                query=active_query,
                context=context,
                history_str=history_text,
                model=selected_model,
                use_groq=use_groq,
            )

            total_t = time.perf_counter() - t_start
            latency_info = {
                "embed": emb_t,
                "retrieval": ret_t,
                "gen": res["latency"],
                "total": total_t,
            }

            st.session_state.memory.add_turn(
                query=active_query,
                response=res["text"],
                sources=hits,
            )

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": res["text"],
                    "sources": hits,
                    "latency": latency_info,
                }
            )

            st.markdown(res["text"])

            st.markdown(
                f"""
                <div>
                    <span class="metric-pill">⚡ Embed: <strong>{emb_t:.3f}s</strong></span>
                    <span class="metric-pill">🔍 Retrieve: <strong>{ret_t:.3f}s</strong></span>
                    <span class="metric-pill">🧠 Gen: <strong>{res['latency']:.3f}s</strong></span>
                    <span class="metric-pill">⏱️ Total: <strong>{total_t:.3f}s</strong></span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if hits:
                with st.expander(f"📑 Citation Cards ({len(hits)} sources)", expanded=True):
                    for i, src in enumerate(hits, start=1):
                        sim = src.get("similarity", 0.0) * 100
                        doc_name = src.get("metadata", {}).get("source", "Campus Doc")
                        page = src.get("metadata", {}).get("page", 1)
                        st.markdown(
                            f"""
                            <div class="citation-card">
                                <div class="citation-header">
                                    <span>📄 Source {i}: {doc_name} (Page {page})</span>
                                    <span class="citation-badge">Cosine Match: {sim:.1f}%</span>
                                </div>
                                <div style="font-size:0.82rem; color:#475569;">{src.get("text", "")}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
