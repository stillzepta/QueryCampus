"""
QueryCampus: Virtual University Receptionist & Campus Concierge.
Streamlit UI Dashboard featuring:
- Role-based Authentication Sidebar (Student vs. Administrator)
- Interactive Chat Interface with rolling memory
- Inline Source Citation Cards with similarity scores
- Automated Ticket Escalation (Lost & Found, Grievances, Low Confidence)
- Administrative Ticket Management & Knowledge Base Dashboard
"""

import os
import time
from pathlib import Path
import streamlit as st

from src.auth import authenticate_user, get_demo_user, User
from src.ingest import DocumentIngestor, SAMPLE_DOCS_DIR
from src.vector_store import ChromaVectorStore
from src.retrieval import CampusRetriever
from src.generator import CampusGenerator, ConversationMemory
from src.ticketing import TicketingSystem


st.set_page_config(
    page_title="QueryCampus - University Concierge & Helpdesk",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
    <style>
    .main-header {
        background: linear-gradient(135deg, #0B3C5D 0%, #1D2731 100%);
        color: white;
        padding: 22px 26px;
        border-radius: 12px;
        margin-bottom: 20px;
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
    .escalation-box {
        background-color: #FFFBEB;
        border: 1px solid #FDE68A;
        border-left: 4px solid #F59E0B;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 12px 0;
        font-size: 0.9rem;
        color: #92400E;
    }
    .role-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .role-student {
        background-color: #E0F2FE;
        color: #0369A1;
    }
    .role-admin {
        background-color: #FEF3C7;
        color: #92400E;
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
    ticketing = TicketingSystem()
    return store, retriever, generator, ticketing


store, retriever, generator, ticketing = init_system()

# User Session Management
if "user" not in st.session_state:
    st.session_state.user = get_demo_user(role="student")

if "memory" not in st.session_state:
    st.session_state.memory = ConversationMemory(max_turns=3)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": f"Hello **{st.session_state.user.name}**! I am **QueryCampus**, your official Virtual University Concierge. Ask me about regulations, fees, hostel curfew, exam policies, or campus facilities.",
            "sources": [],
            "latency": None,
        }
    ]

# ---------------------------------------------------------
# SIDEBAR: Institutional Authentication & System Settings
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### 🔐 Institutional Login")
    curr_user: User = st.session_state.user

    role_class = "role-admin" if curr_user.is_admin else "role-student"
    role_icon = "🛡️" if curr_user.is_admin else "🎓"
    st.markdown(
        f"""
        <div style="background:#F8FAFC; border:1px solid #E2E8F0; padding:12px; border-radius:8px; margin-bottom:12px;">
            <div style="font-size:0.95rem; font-weight:600; color:#1E293B;">{curr_user.name}</div>
            <div style="font-size:0.8rem; color:#64748B;">{curr_user.email}</div>
            <div style="margin-top:6px;">
                <span class="role-badge {role_class}">{role_icon} {curr_user.role.upper()}</span>
                <span style="font-size:0.75rem; color:#64748B; margin-left:6px;">ID: {curr_user.id_number}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("##### Switch Role (Fast Demo Toggle)")
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("🎓 Student Demo", use_container_width=True):
            st.session_state.user = get_demo_user("student")
            st.rerun()
    with c_btn2:
        if st.button("🛡️ Admin Demo", use_container_width=True):
            st.session_state.user = get_demo_user("admin")
            st.rerun()

    with st.expander("Custom Login / Switch Account"):
        with st.form("login_form"):
            login_email = st.text_input("Campus Email", placeholder="student@pesu.pes.edu")
            login_pwd = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In")
            if submitted:
                auth_res = authenticate_user(login_email, login_pwd)
                if auth_res:
                    st.session_state.user = auth_res
                    st.success(f"Signed in as {auth_res.name}")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Invalid institutional credentials.")

    st.markdown("---")
    st.subheader("⚙️ System Control")
    models = generator.list_available_models()
    selected_model = st.selectbox("🧠 Generative Model", options=models, index=0)
    use_groq = st.checkbox("⚡ Cloud Groq Acceleration", value=False)
    top_k = st.slider("🔍 Top-k Document Retrieval", min_value=1, max_value=5, value=2)

    st.markdown("---")
    st.subheader("📁 Knowledge Base")
    st.metric("Total Indexed Chunks", store.count())

    if curr_user.is_admin:
        uploaded_pdf = st.file_uploader("Upload official policy PDF", type=["pdf"])
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
                "content": f"Chat history cleared. How can I help you, {curr_user.name}?",
                "sources": [],
                "latency": None,
            }
        ]
        st.rerun()


# ---------------------------------------------------------
# MAIN VIEW: Student Concierge vs. Administrator Dashboard
# ---------------------------------------------------------
st.markdown(
    """
    <div class="main-header">
        <h1>🎓 QueryCampus</h1>
        <p>RAG-Based Virtual University Receptionist & Campus Concierge</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Role-specific tab navigation
if curr_user.is_admin:
    tab_chat, tab_tickets, tab_knowledge = st.tabs(
        ["💬 Concierge Assistant", "📋 Admin Ticket Dashboard", "📊 Knowledge Base & Stats"]
    )
else:
    tab_chat, tab_tickets = st.tabs(["💬 Concierge Assistant", "🎫 My Support Tickets"])
    tab_knowledge = None


# ---------------------------------------------------------
# TAB 1: Chat Interface & Live Concierge
# ---------------------------------------------------------
with tab_chat:
    st.markdown("##### 💡 Suggested Inquiries:")
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
        if st.button("🔍 Lost ID Card Escalation", use_container_width=True):
            quick_query = "I lost my university student ID card. What should I do?"

    # Render Chat History
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
                with st.expander(f"📑 Official Citation Cards ({len(msg['sources'])} sources)", expanded=False):
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

    user_query = st.chat_input("Type your question about campus guidelines, timings, or office locations...")
    active_query = quick_query or user_query

    if active_query:
        st.session_state.messages.append({"role": "user", "content": active_query})
        with st.chat_message("user"):
            st.markdown(active_query)

        with st.chat_message("assistant"):
            with st.spinner("Retrieving verified university records..."):
                t_start = time.perf_counter()
                hits, emb_t, ret_t = retriever.retrieve(active_query, top_k=top_k)
                confidence_info = retriever.check_confidence(hits)
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

                # Automated Escalation Intent Detection & Confidence Alert
                detected_category = ticketing.detect_escalation_intent(active_query)
                if detected_category or not confidence_info["is_confident"]:
                    cat_name = detected_category or "Administrative Inquiry"
                    st.markdown(
                        f"""
                        <div class="escalation-box">
                            <strong>⚠️ Department Escalation Available:</strong><br>
                            Your inquiry involves <em>{cat_name}</em>. If the official document records do not completely resolve your situation, you can immediately file an official support ticket.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    with st.expander(f"🎫 Open Official {cat_name} Ticket", expanded=False):
                        with st.form(f"ticket_quick_{int(time.time())}"):
                            t_title = st.text_input("Ticket Title", value=f"Inquiry regarding: {active_query[:50]}")
                            t_desc = st.text_area("Detailed Description", value=f"Student inquiry: {active_query}")
                            t_prio = st.selectbox("Priority", ["Medium", "High", "Critical", "Low"])
                            if st.form_submit_button("Submit Official Ticket"):
                                created = ticketing.create_ticket(
                                    user_email=curr_user.email,
                                    user_name=curr_user.name,
                                    category=cat_name,
                                    title=t_title,
                                    description=t_desc,
                                    priority=t_prio,
                                )
                                st.success(f"Ticket {created.ticket_number} created successfully! Track it in the Tickets tab.")

                if hits:
                    with st.expander(f"📑 Official Citation Cards ({len(hits)} sources)", expanded=True):
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


# ---------------------------------------------------------
# TAB 2: Support Tickets & Admin Dashboard
# ---------------------------------------------------------
with tab_tickets:
    if curr_user.is_admin:
        st.subheader("📋 Administrative Support & Escalations Desk")
        st.caption("Review, triage, and resolve student support tickets, lost & found claims, and grievances.")

        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            status_filter = st.selectbox("Filter Status", ["All", "Open", "In Review", "Resolved", "Closed"])
        with col_f2:
            st.metric("Total Tickets", len(ticketing.get_all_tickets()))

        all_tickets = ticketing.get_all_tickets(status_filter=status_filter)
        if not all_tickets:
            st.info("No tickets match the selected status.")
        else:
            for t in all_tickets:
                with st.expander(f"[{t.ticket_number}] {t.category}: {t.title} ({t.status}) - Priority: {t.priority}"):
                    st.write(f"**Submitted By:** {t.user_name} ({t.user_email})")
                    st.write(f"**Created At:** {t.created_at}")
                    st.write(f"**Details:** {t.description}")
                    if t.admin_notes:
                        st.info(f"**Admin Remarks:** {t.admin_notes}")

                    with st.form(f"update_ticket_{t.id}"):
                        c_u1, c_u2 = st.columns([1, 2])
                        with c_u1:
                            new_st = st.selectbox("Update Status", ["Open", "In Review", "Resolved", "Closed"], index=["Open", "In Review", "Resolved", "Closed"].index(t.status))
                        with c_u2:
                            new_notes = st.text_input("Administrator Action Notes", value=t.admin_notes or "")

                        if st.form_submit_button("Save Update"):
                            ticketing.update_ticket_status(t.id, new_st, new_notes)
                            st.success(f"Ticket {t.ticket_number} updated to {new_st}!")
                            time.sleep(0.5)
                            st.rerun()

    else:
        st.subheader("🎫 My Support & Escalation Tickets")
        st.caption("Track the status of tickets you have submitted for Lost & Found, Maintenance, or Academic Grievances.")

        with st.expander("➕ Submit a New Support Ticket", expanded=False):
            with st.form("manual_ticket_form"):
                cat = st.selectbox("Category", ["Lost & Found", "Hostel Maintenance", "Academic Escalation", "Fee Grievance", "General Admin"])
                title = st.text_input("Summary Title", placeholder="e.g. Lost Black Wallet in Central Library 2nd Floor")
                desc = st.text_area("Detailed Description", placeholder="Please provide specific location, date, time, and identifying details...")
                prio = st.selectbox("Priority", ["Low", "Medium", "High", "Critical"], index=1)
                if st.form_submit_button("Submit Ticket"):
                    if title and desc:
                        t = ticketing.create_ticket(
                            user_email=curr_user.email,
                            user_name=curr_user.name,
                            category=cat,
                            title=title,
                            description=desc,
                            priority=prio,
                        )
                        st.success(f"Ticket {t.ticket_number} created! Department administrators will review it.")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.warning("Please provide both a title and description.")

        my_tickets = ticketing.get_user_tickets(curr_user.email)
        if not my_tickets:
            st.info("You currently have no active support tickets.")
        else:
            for t in my_tickets:
                status_color = "🟢" if t.status == "Resolved" else ("🟡" if t.status == "In Review" else "🔵")
                with st.expander(f"{status_color} [{t.ticket_number}] {t.category}: {t.title} — **{t.status}**"):
                    st.write(f"**Submitted On:** {t.created_at}")
                    st.write(f"**Priority:** {t.priority}")
                    st.write(f"**Description:** {t.description}")
                    if t.admin_notes:
                        st.success(f"**Official Resolution / Admin Note:** {t.admin_notes}")
                    else:
                        st.caption("Waiting for administrative review.")


# ---------------------------------------------------------
# TAB 3: Knowledge Base & System Health (Admin Only)
# ---------------------------------------------------------
if curr_user.is_admin and tab_knowledge:
    with tab_knowledge:
        st.subheader("📊 Knowledge Base & System Architecture")
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Indexed Chunks", store.count())
        col_m2.metric("Chroma Collection", store.collection_name)
        col_m3.metric("SQLite DB Status", "Connected (data/db/campus.db)")

        st.markdown("#### Institutional Document Repositories")
        docs = list(SAMPLE_DOCS_DIR.glob("*.*"))
        for d in docs:
            st.write(f"📄 `{d.name}` ({d.stat().st_size} bytes)")
