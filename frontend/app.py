"""
QueryCampus: Virtual University Receptionist & Campus Concierge.
Streamlit UI Dashboard featuring:
- Role-based Authentication Sidebar (Student vs. Administrator)
- Interactive Chat Interface powered by backend_interface facade
- Inline Source Citation Cards with similarity scores
- Multi-modal Notice Board & Map image parser
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
from src.backend_interface import (
    process_student_turn,
    create_escalation_ticket,
    get_student_tickets,
    get_admin_tickets,
    update_admin_ticket,
)


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
    return store


store = init_system()

# User Session Management
if "user" not in st.session_state:
    st.session_state.user = get_demo_user(role="student")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": f"Hello **{st.session_state.user.name}**! I am **QueryCampus**, your official Virtual University Concierge. Ask me about academic regulations, fees, hostel rules, exam procedures, office locations, or upload a photo of a notice board.",
            "citations": [],
            "latency_ms": None,
            "mode_used": None,
            "confidence_score": None,
            "ticket_draft": None,
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
    inference_mode = st.radio(
        "🧠 Inference Route",
        options=["groq", "ollama"],
        index=0,
        format_func=lambda x: "⚡ Groq Cloud (Sub-second)" if x == "groq" else "🔒 Ollama Local (Private)",
    )

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
        st.session_state.chat_history = []
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": f"Chat history cleared. How can I help you, {curr_user.name}?",
                "citations": [],
                "latency_ms": None,
                "mode_used": None,
                "confidence_score": None,
                "ticket_draft": None,
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

    # Optional multi-modal notice board image upload
    with st.expander("📸 Upload Physical Notice Board / Exam Seating / Map Photo (Optional)", expanded=False):
        uploaded_notice_img = st.file_uploader(
            "Upload image to analyze and cross-reference with campus regulations",
            type=["png", "jpg", "jpeg"],
            key="notice_uploader",
        )

    # Render Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            if msg.get("latency_ms"):
                conf_pct = (msg.get("confidence_score") or 0.0) * 100
                st.markdown(
                    f"""
                    <div>
                        <span class="metric-pill">⏱️ Latency: <strong>{msg['latency_ms']} ms</strong></span>
                        <span class="metric-pill">🧠 Mode: <strong>{msg.get('mode_used', 'LLM')}</strong></span>
                        <span class="metric-pill">🎯 Confidence: <strong>{conf_pct:.1f}%</strong></span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if msg.get("citations"):
                with st.expander(f"📑 Official Citation Cards ({len(msg['citations'])} sources)", expanded=False):
                    for i, src in enumerate(msg["citations"], start=1):
                        st.markdown(
                            f"""
                            <div class="citation-card">
                                <div class="citation-header">
                                    <span>📄 Source {i}: {src.get('source')} (Page {src.get('page')})</span>
                                    <span class="citation-badge">Section: {src.get('section', 'General')}</span>
                                </div>
                                <div style="font-size:0.82rem; color:#475569;">{src.get('snippet', '')}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

    user_query = st.chat_input("Type your question about campus guidelines, timings, or office locations...")
    active_query = quick_query or user_query

    if active_query:
        # Append to UI and chat history
        st.session_state.messages.append({"role": "user", "content": active_query})
        st.session_state.chat_history.append({"role": "user", "content": active_query})
        with st.chat_message("user"):
            st.markdown(active_query)

        with st.chat_message("assistant"):
            with st.spinner("Processing inquiry via QueryCampus backend..."):
                img_bytes = uploaded_notice_img.getvalue() if uploaded_notice_img else None
                user_session = {
                    "name": curr_user.name,
                    "email": curr_user.email,
                    "role": curr_user.role,
                    "id_number": curr_user.id_number,
                }

                # Single unified facade call to Krishna's backend
                turn_result = process_student_turn(
                    query=active_query,
                    user_session=user_session,
                    chat_history=st.session_state.chat_history,
                    inference_mode=inference_mode,
                    uploaded_image=img_bytes,
                )

                st.session_state.chat_history.append({"role": "assistant", "content": turn_result["answer"]})
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": turn_result["answer"],
                        "citations": turn_result["citations"],
                        "latency_ms": turn_result["latency_ms"],
                        "mode_used": turn_result["mode_used"],
                        "confidence_score": turn_result["confidence_score"],
                        "ticket_draft": turn_result.get("ticket_draft"),
                    }
                )

                st.markdown(turn_result["answer"])

                conf_pct = turn_result["confidence_score"] * 100
                st.markdown(
                    f"""
                    <div>
                        <span class="metric-pill">⏱️ Latency: <strong>{turn_result['latency_ms']} ms</strong></span>
                        <span class="metric-pill">🧠 Mode: <strong>{turn_result['mode_used']}</strong></span>
                        <span class="metric-pill">🎯 Confidence: <strong>{conf_pct:.1f}%</strong></span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Automated Department Escalation Prompt
                if turn_result["requires_ticket"] and turn_result.get("ticket_draft"):
                    draft = turn_result["ticket_draft"]
                    st.markdown(
                        f"""
                        <div class="escalation-box">
                            <strong>⚠️ Official Escalation Recommended:</strong><br>
                            This matter involves <em>{draft['category']}</em> or requires verified department action.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    with st.expander(f"🎫 File Official {draft['category']} Ticket", expanded=False):
                        with st.form(f"ticket_quick_{int(time.time())}"):
                            t_title = st.text_input("Ticket Summary", value=draft["summary"])
                            t_desc = st.text_area("Inquiry Details", value=draft["query_text"])
                            t_prio = st.selectbox("Priority", ["Medium", "High", "Critical", "Low"])
                            if st.form_submit_button("Submit Ticket to Department"):
                                created = create_escalation_ticket(
                                    ticket_data={"category": draft["category"], "summary": t_title, "query_text": t_desc, "priority": t_prio},
                                    user_session=user_session,
                                )
                                st.success(f"Ticket {created['ticket_number']} submitted! Track it in the Tickets tab.")

                # Citations
                if turn_result["citations"]:
                    with st.expander(f"📑 Official Citation Cards ({len(turn_result['citations'])} sources)", expanded=True):
                        for i, src in enumerate(turn_result["citations"], start=1):
                            st.markdown(
                                f"""
                                <div class="citation-card">
                                    <div class="citation-header">
                                        <span>📄 Source {i}: {src.get('source')} (Page {src.get('page')})</span>
                                        <span class="citation-badge">Section: {src.get('section', 'General')}</span>
                                    </div>
                                    <div style="font-size:0.82rem; color:#475569;">{src.get('snippet', '')}</div>
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
            all_tkts = get_admin_tickets(status_filter=None)
            st.metric("Total System Tickets", len(all_tkts))

        filtered_tickets = get_admin_tickets(status_filter=status_filter)
        if not filtered_tickets:
            st.info("No tickets match the selected status.")
        else:
            for t in filtered_tickets:
                with st.expander(f"[{t['ticket_number']}] {t['category']}: {t['title']} ({t['status']}) - Priority: {t['priority']}"):
                    st.write(f"**Submitted By:** {t['user_name']} ({t['user_email']})")
                    st.write(f"**Created At:** {t['created_at']}")
                    st.write(f"**Details:** {t['description']}")
                    if t.get("admin_notes"):
                        st.info(f"**Admin Remarks:** {t['admin_notes']}")

                    with st.form(f"update_ticket_{t['id']}"):
                        c_u1, c_u2 = st.columns([1, 2])
                        with c_u1:
                            new_st = st.selectbox(
                                "Update Status",
                                ["Open", "In Review", "Resolved", "Closed"],
                                index=["Open", "In Review", "Resolved", "Closed"].index(t["status"]),
                            )
                        with c_u2:
                            new_notes = st.text_input("Administrator Action Notes", value=t.get("admin_notes") or "")

                        if st.form_submit_button("Save Update"):
                            update_admin_ticket(t["id"], new_st, new_notes)
                            st.success(f"Ticket {t['ticket_number']} updated to {new_st}!")
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
                        user_sess = {"name": curr_user.name, "email": curr_user.email}
                        t_res = create_escalation_ticket(
                            {"category": cat, "summary": title, "query_text": desc, "priority": prio},
                            user_session=user_sess,
                        )
                        st.success(f"Ticket {t_res['ticket_number']} created! Department administrators will review it.")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.warning("Please provide both a title and description.")

        my_tickets = get_student_tickets(curr_user.email)
        if not my_tickets:
            st.info("You currently have no active support tickets.")
        else:
            for t in my_tickets:
                status_color = "🟢" if t["status"] == "Resolved" else ("🟡" if t["status"] == "In Review" else "🔵")
                with st.expander(f"{status_color} [{t['ticket_number']}] {t['category']}: {t['title']} — **{t['status']}**"):
                    st.write(f"**Submitted On:** {t['created_at']}")
                    st.write(f"**Priority:** {t['priority']}")
                    st.write(f"**Description:** {t['description']}")
                    if t.get("admin_notes"):
                        st.success(f"**Official Resolution / Admin Note:** {t['admin_notes']}")
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
        col_m3.metric("SQLite DB Status", "Connected (data/db/querycampus.db)")

        st.markdown("#### Institutional Document Repositories")
        docs = list(SAMPLE_DOCS_DIR.glob("*.*"))
        for d in docs:
            st.write(f"📄 `{d.name}` ({d.stat().st_size} bytes)")
