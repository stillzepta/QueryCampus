"""
QueryCampus: Virtual University Receptionist & Campus Concierge.
Crafted for Bosscoder College featuring:
- Deep purple sidebar (#21133D)
- Very light lavender main background (#F7F5FF)
- White chat cards with rounded corners
- Lime green buttons (#D6F36A)
- Purple gradient accents (#21133D -> #6842C2 -> #A78BFA)
- Small animated AI assistant indicator
- Aussie (AI Campus Receptionist) & Serina Mehra (Active Student)
"""

import os
import time
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

from src.auth import authenticate_user, get_demo_user, User
from src.ingest import DocumentIngestor, SAMPLE_DOCS_DIR
from src.vector_store import ChromaVectorStore
from src.retrieval import CampusRetriever
from src.generator import CampusGenerator, ConversationMemory
from src.ticketing import TicketingSystem


st.set_page_config(
    page_title="QueryCampus • Bosscoder College Reception Desk",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# STYLES: Bosscoder College Reception Aesthetic
# Colors:
# - #21133D: Deep purple (Sidebar & Dark Contrast)
# - #6842C2: Royal purple (Purple Gradient Accents)
# - #A78BFA: Soft lavender (Borders & Glows)
# - #D6F36A: Lime green (Buttons, Bell, Active Indicators)
# - #F7F5FF: Very light lavender (Main Background)
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Cinzel:wght@600;700;800;900&family=JetBrains+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Very Light Lavender Main Background */
    .stApp {
        background-color: #F7F5FF !important;
        color: #21133D !important;
    }

    /* Deep Purple Sidebar */
    [data-testid="stSidebar"] {
        background-color: #21133D !important;
        border-right: 1.5px solid rgba(167, 139, 250, 0.3) !important;
        box-shadow: 4px 0 24px rgba(33, 19, 61, 0.3) !important;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] h5 {
        color: #F7F5FF !important;
    }
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] select, [data-testid="stSidebar"] textarea {
        background: #2E1B54 !important;
        border: 1.5px solid rgba(167, 139, 250, 0.35) !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
    }
    [data-testid="stSidebar"] input:focus, [data-testid="stSidebar"] select:focus {
        border-color: #D6F36A !important;
        box-shadow: 0 0 10px rgba(214, 243, 106, 0.4) !important;
    }

    /* =========================================================
       1. GLOBAL BUTTON STYLING (LIME GREEN WITH BOLD DEEP PURPLE TEXT)
       ========================================================= */
    button,
    button[data-testid*="stBaseButton"],
    .stButton > button,
    [data-testid="stSidebar"] button,
    [data-testid="stFormSubmitButton"] > button {
        background-color: #D6F36A !important;
        border: none !important;
        border-radius: 24px !important;
        padding: 9px 20px !important;
        box-shadow: 0 4px 14px rgba(214, 243, 106, 0.4) !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }

    /* ALL TEXT INSIDE ANY BUTTON MUST BE DEEP PURPLE AND BOLD */
    button *,
    button p,
    button span,
    button div,
    button[data-testid*="stBaseButton"] *,
    button[data-testid*="stBaseButton"] p,
    button[data-testid*="stBaseButton"] span,
    button[data-testid*="stBaseButton"] div,
    .stButton > button *,
    .stButton > button p,
    .stButton > button span,
    .stButton > button div,
    [data-testid="stSidebar"] button *,
    [data-testid="stSidebar"] button p,
    [data-testid="stSidebar"] button span,
    [data-testid="stSidebar"] button div,
    [data-testid="stFormSubmitButton"] > button *,
    [data-testid="stFormSubmitButton"] > button p,
    [data-testid="stFormSubmitButton"] > button span,
    [data-testid="stFormSubmitButton"] > button div {
        color: #21133D !important;
        font-weight: 800 !important;
        font-size: 0.92rem !important;
        opacity: 1 !important;
        white-space: normal !important;
        text-overflow: unset !important;
    }

    /* BUTTON HOVER EFFECT */
    button:hover,
    button[data-testid*="stBaseButton"]:hover,
    .stButton > button:hover,
    [data-testid="stSidebar"] button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        background-color: #E4FFA0 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(214, 243, 106, 0.6) !important;
    }
    button:hover *,
    .stButton > button:hover *,
    [data-testid="stSidebar"] button:hover * {
        color: #21133D !important;
    }

    /* =========================================================
       2. TABS STYLING (REMOVE THIN LINE & MAKE ALL TABS VISIBLE)
       ========================================================= */
    /* Remove default thin line under tabs */
    .stTabs [data-baseweb="tab-border"],
    div[data-baseweb="tab-border"],
    .stTabs [data-baseweb="tab-highlight"],
    div[data-baseweb="tab-highlight"],
    .stTabs hr,
    [data-testid="stTabs"] hr {
        display: none !important;
        height: 0px !important;
        border: none !important;
        visibility: hidden !important;
    }

    /* Tab bar container: sleek white pill */
    .stTabs [data-baseweb="tab-list"] {
        display: inline-flex !important;
        gap: 12px !important;
        background: #FFFFFF !important;
        border: 1.5px solid rgba(104, 66, 194, 0.22) !important;
        padding: 8px 12px !important;
        border-radius: 24px !important;
        box-shadow: 0 4px 20px rgba(33, 19, 61, 0.06) !important;
        margin-bottom: 24px !important;
    }

    /* Unselected tabs: Clearly visible soft-purple pill with bold deep-purple text */
    .stTabs [data-baseweb="tab"]:not([aria-selected="true"]),
    .stTabs button[role="tab"]:not([aria-selected="true"]) {
        background-color: #EDE8F9 !important;
        border: 1.5px solid #C4B5FD !important;
        border-radius: 16px !important;
        padding: 10px 24px !important;
        transition: all 0.2s ease !important;
        opacity: 1 !important;
        visibility: visible !important;
    }

    /* UNSELECTED TAB TEXT: ALWAYS VISIBLE BOLD DEEP PURPLE (NOT JUST ON HOVER) */
    .stTabs [data-baseweb="tab"]:not([aria-selected="true"]) *,
    .stTabs [data-baseweb="tab"]:not([aria-selected="true"]) p,
    .stTabs [data-baseweb="tab"]:not([aria-selected="true"]) span,
    .stTabs [data-baseweb="tab"]:not([aria-selected="true"]) div,
    .stTabs button[role="tab"]:not([aria-selected="true"]) *,
    .stTabs button[role="tab"]:not([aria-selected="true"]) p,
    .stTabs button[role="tab"]:not([aria-selected="true"]) span,
    .stTabs button[role="tab"]:not([aria-selected="true"]) div {
        color: #21133D !important;
        font-weight: 800 !important;
        font-size: 0.94rem !important;
        opacity: 1 !important;
        visibility: visible !important;
    }

    .stTabs [data-baseweb="tab"]:not([aria-selected="true"]):hover,
    .stTabs button[role="tab"]:not([aria-selected="true"]):hover {
        background-color: #DDD4F7 !important;
        border-color: #6842C2 !important;
        transform: translateY(-1px) !important;
    }

    /* Active Selected Tab: Rich Purple Gradient with White Text */
    .stTabs [data-baseweb="tab"][aria-selected="true"],
    .stTabs button[role="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #21133D 0%, #6842C2 100%) !important;
        border: 1.5px solid #6842C2 !important;
        border-radius: 16px !important;
        padding: 10px 24px !important;
        box-shadow: 0 4px 16px rgba(104, 66, 194, 0.35) !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] *,
    .stTabs [data-baseweb="tab"][aria-selected="true"] p,
    .stTabs [data-baseweb="tab"][aria-selected="true"] span,
    .stTabs [data-baseweb="tab"][aria-selected="true"] div,
    .stTabs button[role="tab"][aria-selected="true"] *,
    .stTabs button[role="tab"][aria-selected="true"] p,
    .stTabs button[role="tab"][aria-selected="true"] span,
    .stTabs button[role="tab"][aria-selected="true"] div {
        color: #FFFFFF !important;
        font-weight: 800 !important;
        font-size: 0.94rem !important;
    }

    /* Top Banner with Purple Gradient Accent */
    .campus-banner {
        background: linear-gradient(135deg, #21133D 0%, #4D2689 50%, #6842C2 100%);
        border: 1.5px solid rgba(167, 139, 250, 0.35);
        border-radius: 22px;
        padding: 26px 36px;
        margin-bottom: 24px;
        box-shadow: 0 16px 40px rgba(33, 19, 61, 0.16);
        position: relative;
        overflow: hidden;
        color: #FFFFFF;
    }
    .campus-banner::before {
        content: "";
        position: absolute;
        top: -60px;
        right: -60px;
        width: 220px;
        height: 220px;
        background: radial-gradient(circle, rgba(214, 243, 106, 0.25) 0%, rgba(104, 66, 194, 0.1) 60%, transparent 80%);
        border-radius: 50%;
    }
    .campus-banner-title {
        font-family: 'Cinzel', serif;
        font-size: 2.1rem;
        font-weight: 800;
        color: #FFFFFF !important;
        margin: 0 0 6px 0;
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .campus-banner-sub {
        color: #D6F36A;
        font-size: 0.98rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin: 0;
    }
    .campus-badge-row {
        margin-top: 14px;
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        align-items: center;
    }
    .live-desk-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(214, 243, 106, 0.2);
        border: 1.5px solid #D6F36A;
        color: #D6F36A;
        font-size: 0.8rem;
        font-weight: 800;
        padding: 5px 14px;
        border-radius: 20px;
    }
    .desk-hours-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255, 255, 255, 0.12);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: #F7F5FF;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 5px 14px;
        border-radius: 20px;
    }

    /* Small Animated AI Assistant Indicator */
    .ai-assistant-indicator {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(33, 19, 61, 0.08);
        border: 1px solid rgba(104, 66, 194, 0.25);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 800;
        color: #21133D;
    }
    .ai-orb-core {
        width: 9px;
        height: 9px;
        background-color: #D6F36A;
        border-radius: 50%;
        box-shadow: 0 0 8px #D6F36A;
        display: inline-block;
        animation: aiBreathe 1.8s infinite ease-in-out;
    }
    @keyframes aiBreathe {
        0%, 100% { transform: scale(0.85); box-shadow: 0 0 4px #D6F36A; }
        50% { transform: scale(1.25); box-shadow: 0 0 12px #D6F36A; }
    }

    /* Reception Desk Lobby Hero with Purple Gradient */
    .desk-hero-card {
        background: linear-gradient(135deg, #21133D 0%, #4D2689 60%, #6842C2 100%);
        border: 2px solid rgba(167, 139, 250, 0.35);
        border-radius: 22px;
        padding: 30px;
        color: #F7F5FF;
        box-shadow: 0 16px 40px rgba(33, 19, 61, 0.18);
        display: flex;
        gap: 26px;
        align-items: center;
        position: relative;
    }
    .receptionist-avatar-frame {
        width: 110px;
        height: 110px;
        border-radius: 50%;
        background: linear-gradient(135deg, #D6F36A, #A78BFA);
        padding: 4px;
        flex-shrink: 0;
        box-shadow: 0 0 25px rgba(214, 243, 106, 0.4);
        position: relative;
    }
    .receptionist-avatar-img {
        width: 100%;
        height: 100%;
        border-radius: 50%;
        background: #21133D;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 3.6rem;
    }
    .avatar-status-dot {
        position: absolute;
        bottom: 4px;
        right: 4px;
        width: 20px;
        height: 20px;
        background: #D6F36A;
        border: 3.5px solid #21133D;
        border-radius: 50%;
        box-shadow: 0 0 10px #D6F36A;
    }
    .receptionist-dialogue {
        background: rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-left: 4px solid #D6F36A;
        border-radius: 14px;
        padding: 18px 22px;
        margin-top: 10px;
        color: #FFFFFF;
        font-size: 1rem;
        line-height: 1.6;
    }
    .receptionist-dialogue strong {
        color: #D6F36A;
    }
    .desk-nameplate {
        font-family: 'Cinzel', serif;
        font-size: 0.85rem;
        letter-spacing: 2px;
        color: #D6F36A;
        font-weight: 800;
        margin-bottom: 4px;
        text-transform: uppercase;
    }
    .receptionist-name {
        font-size: 1.6rem;
        font-weight: 800;
        color: #FFFFFF;
        margin: 0;
    }

    /* Kiosk Interactive Header */
    .kiosk-header {
        background: #21133D;
        border: 1.5px solid rgba(167, 139, 250, 0.3);
        border-radius: 18px;
        padding: 18px 26px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 8px 28px rgba(33, 19, 61, 0.15);
        color: #FFFFFF;
    }
    .kiosk-receptionist-info {
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .kiosk-avatar {
        width: 52px;
        height: 52px;
        border-radius: 50%;
        background: #6842C2;
        border: 2px solid #D6F36A;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.7rem;
    }
    .kiosk-title {
        font-weight: 800;
        font-size: 1.15rem;
        color: #FFFFFF;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .kiosk-status {
        font-size: 0.82rem;
        color: #D6F36A;
        font-weight: 700;
    }

    /* White Chat Cards with Rounded Corners */
    [data-testid="stChatMessage"] {
        background-color: #FFFFFF !important;
        border: 1px solid rgba(104, 66, 194, 0.16) !important;
        border-radius: 20px !important;
        padding: 18px 24px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 8px 24px rgba(33, 19, 61, 0.05) !important;
        color: #21133D !important;
    }
    [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] span {
        color: #21133D !important;
    }

    .official-seal-tag {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.74rem;
        font-weight: 800;
        color: #6842C2;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .citation-card {
        border-left: 3.5px solid #6842C2;
        background-color: #F7F5FF;
        padding: 14px 18px;
        border-radius: 0 12px 12px 0;
        margin: 10px 0;
        border-top: 1px solid rgba(104, 66, 194, 0.12);
        border-right: 1px solid rgba(104, 66, 194, 0.12);
        border-bottom: 1px solid rgba(104, 66, 194, 0.12);
        color: #21133D;
    }
    .citation-header {
        font-weight: 700;
        color: #21133D;
        font-size: 0.85rem;
        margin-bottom: 6px;
        display: flex;
        justify-content: space-between;
    }
    .citation-badge {
        background-color: #D6F36A;
        color: #21133D;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.72rem;
        font-weight: 800;
    }
    .metric-pill {
        display: inline-flex;
        align-items: center;
        background-color: #F7F5FF;
        border: 1px solid rgba(104, 66, 194, 0.2);
        border-radius: 8px;
        padding: 4px 10px;
        font-size: 0.76rem;
        color: #64557E;
        margin-right: 8px;
        margin-top: 8px;
    }
    .metric-pill strong {
        color: #21133D;
    }
    .escalation-box {
        background-color: #FFFBEB;
        border: 1px solid #FDE68A;
        border-left: 4px solid #F59E0B;
        padding: 16px 20px;
        border-radius: 12px;
        margin: 14px 0;
        font-size: 0.92rem;
        color: #92400E;
    }

    /* Auth Badges */
    .role-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 16px;
        font-weight: 800;
        font-size: 0.8rem;
    }
    .role-student {
        background-color: #D6F36A !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
    }
    .role-admin {
        background-color: #FEF3C7 !important;
        color: #92400E !important;
        -webkit-text-fill-color: #92400E !important;
    }

    /* Chat Input Styling — works in both light & dark mode */
    [data-testid="stChatInput"],
    [data-testid="stBottom"] [data-testid="stChatInput"],
    section[data-testid="stBottom"] > div {
        background-color: #1C0F35 !important;
        border-radius: 30px !important;
        border: 1.5px solid #6842C2 !important;
        box-shadow: 0 0 0 1px rgba(167,139,250,0.2), 0 4px 20px rgba(33,19,61,0.3) !important;
    }
    [data-testid="stChatInput"]:focus-within {
        border-color: #A78BFA !important;
        box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.25) !important;
    }

    /* Typed text — lime green, visible on dark background */
    [data-testid="stChatInput"] textarea,
    [data-testid="stChatInputTextArea"] textarea,
    div[data-testid="stChatInput"] textarea,
    section[data-testid="stBottom"] textarea,
    .stChatInput textarea,
    textarea[data-testid],
    div[class*="chatInput"] textarea,
    [data-testid="stBottom"] textarea {
        color: #D6F36A !important;
        -webkit-text-fill-color: #D6F36A !important;
        background-color: transparent !important;
        caret-color: #D6F36A !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }

    /* Placeholder text — soft lime at 55% opacity */
    [data-testid="stChatInput"] textarea::placeholder,
    section[data-testid="stBottom"] textarea::placeholder,
    [data-testid="stBottom"] textarea::placeholder {
        color: rgba(214, 243, 106, 0.55) !important;
        -webkit-text-fill-color: rgba(214, 243, 106, 0.55) !important;
        font-weight: 400 !important;
    }

    /* Send button (arrow) inside chat input — lime green */
    [data-testid="stChatInput"] button,
    [data-testid="stBottom"] button[kind="primaryFormSubmit"] {
        background-color: #D6F36A !important;
        border-radius: 50% !important;
        color: #21133D !important;
    }
    [data-testid="stChatInput"] button svg,
    [data-testid="stBottom"] button svg {
        fill: #21133D !important;
        color: #21133D !important;
    }

    /* Bottom bar background — match dark purple */
    [data-testid="stBottom"],
    section[data-testid="stBottom"] {
        background-color: #F7F5FF !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# SYSTEM INITIALIZATION
# ---------------------------------------------------------
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

# State Management
if "user" not in st.session_state:
    st.session_state.user = get_demo_user(role="student")

if "memory" not in st.session_state:
    st.session_state.memory = ConversationMemory(max_turns=3)

# UI state: "lobby" (visitor in reception hall) or "kiosk" (interacting at receptionist desk)
if "reception_mode" not in st.session_state:
    st.session_state.reception_mode = "lobby"

if "bell_count" not in st.session_state:
    st.session_state.bell_count = 0

if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": f"Good evening, **{st.session_state.user.name}**! Welcome to the Bosscoder College Reception & Concierge Desk. I am **Aussie**, your AI Receptionist. I have access to official handbooks, exam policies, fee guidelines, and hostel rules. How may I direct or assist you today?",
            "sources": [],
            "latency": None,
        }
    ]


# ---------------------------------------------------------
# HELPER: Audio Synthesizer (Pure JS Web Audio Bell Chime)
# ---------------------------------------------------------
def render_bell_chime_trigger():
    """Rings a realistic brass desk service bell using Web Audio API."""
    chime_html = """
    <script>
    (function() {
        try {
            var AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            var ctx = new AudioContext();
            var now = ctx.currentTime;

            // Fundamental brass chime frequency
            var osc1 = ctx.createOscillator();
            var gain1 = ctx.createGain();
            osc1.type = 'sine';
            osc1.frequency.setValueAtTime(1864.66, now); // A#6
            gain1.gain.setValueAtTime(0.45, now);
            gain1.gain.exponentialRampToValueAtTime(0.0001, now + 1.3);
            osc1.connect(gain1);
            gain1.connect(ctx.destination);
            osc1.start(now);
            osc1.stop(now + 1.3);

            // Shimmer overtone
            var osc2 = ctx.createOscillator();
            var gain2 = ctx.createGain();
            osc2.type = 'sine';
            osc2.frequency.setValueAtTime(3729.31, now); // A#7
            gain2.gain.setValueAtTime(0.2, now);
            gain2.gain.exponentialRampToValueAtTime(0.0001, now + 0.95);
            osc2.connect(gain2);
            gain2.connect(ctx.destination);
            osc2.start(now);
            osc2.stop(now + 0.95);
        } catch(e) {
            console.log("Audio bell chime:", e);
        }
    })();
    </script>
    """
    components.html(chime_html, height=0, width=0)


# ---------------------------------------------------------
# SIDEBAR: DEEP PURPLE INSTITUTIONAL ACCESS
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### 🏛️ Bosscoder Portal")
    curr_user: User = st.session_state.user

    role_class = "role-admin" if curr_user.is_admin else "role-student"
    role_icon = "🛡️" if curr_user.is_admin else "🎓"

    st.markdown(
        f"""
        <div style="background:#2E1B54; border:1px solid rgba(167, 139, 250, 0.4); padding:18px; border-radius:16px; margin-bottom:16px; box-shadow:0 4px 16px rgba(0,0,0,0.25);">
            <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:1px; color:#D6F36A; font-weight:800;">Active Student</div>
            <div style="font-size:1.15rem; font-weight:800; color:#FFFFFF; margin-top:2px;">{curr_user.name}</div>
            <div style="font-size:0.82rem; color:#A78BFA;">{curr_user.email}</div>
            <div style="margin-top:10px; display:flex; align-items:center; gap:8px;">
                <span class="role-badge {role_class}">{role_icon} {curr_user.role.upper()}</span>
                <span style="font-size:0.75rem; color:#D6F36A; font-weight:600;">ID: {curr_user.id_number}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("🔑 Switch Account / Institutional Sign In"):
        with st.form("sidebar_login"):
            login_email = st.text_input("Campus Email", placeholder="serina.mehra@bosscoder.edu")
            login_pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In"):
                auth_res = authenticate_user(login_email, login_pwd)
                if auth_res:
                    st.session_state.user = auth_res
                    st.success(f"Welcome, {auth_res.name}")
                    time.sleep(0.4)
                    st.rerun()
                else:
                    st.error("Invalid credentials.")

    st.markdown("---")
    st.subheader("⚙️ Aussie Brain Settings")
    models = generator.list_available_models()
    selected_model = st.selectbox("🧠 Reasoning Model", options=models, index=0)
    use_groq = st.checkbox("⚡ Cloud Groq Acceleration", value=False)
    top_k = st.slider("🔍 Document Evidence Depth (Top-k)", min_value=1, max_value=5, value=2)

    st.markdown("---")
    st.subheader("📚 Knowledge Base")
    st.metric("Official Documents Indexed", f"{store.count()} sections")

    if curr_user.is_admin:
        uploaded_pdf = st.file_uploader("Upload Policy / Circular PDF", type=["pdf", "txt"])
        if uploaded_pdf and st.button("Index into Aussie's RAG"):
            with st.spinner("Ingesting & chunking document..."):
                save_path = SAMPLE_DOCS_DIR / uploaded_pdf.name
                os.makedirs(SAMPLE_DOCS_DIR, exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(uploaded_pdf.getbuffer())
                ingestor = DocumentIngestor()
                new_chunks = ingestor.load_directory()
                added = store.add_chunks(new_chunks)
                st.success(f"Successfully indexed {added} new sections!")
                time.sleep(0.6)
                st.rerun()

    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.memory.clear()
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": f"Chat history refreshed. How may I assist you at the front desk, {curr_user.name}?",
                "sources": [],
                "latency": None,
            }
        ]
        st.session_state.reception_mode = "lobby"
        st.rerun()


# ---------------------------------------------------------
# MAIN BANNER: PURPLE GRADIENT ACCENT
# ---------------------------------------------------------
st.markdown(
    """
    <div class="campus-banner">
        <div class="campus-banner-title">
            <span>🏛️</span>
            <span>QueryCampus • Bosscoder College Welcome Center</span>
        </div>
        <p class="campus-banner-sub">AI Virtual Reception Desk & Department Concierge Service</p>
        <div class="campus-badge-row">
            <span class="live-desk-pill">
                <span class="ai-orb-core"></span>
                <span>Aussie Online • Counter 01</span>
            </span>
            <span class="desk-hours-pill">🕒 Desk Hours: 08:00 AM – 08:00 PM IST</span>
            <span class="desk-hours-pill">📍 Location: Administration Pavilion, Ground Floor</span>
            <span class="desk-hours-pill">⚡ Neural RAG Grounding</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# VIEW CONTROLLER: TABS
# ---------------------------------------------------------
if curr_user.is_admin:
    tab_reception, tab_tickets, tab_records = st.tabs(
        ["🛎️ Reception & Kiosk", "📋 Admin Ticket Triage Desk", "📊 Campus Records & Knowledge Base"]
    )
else:
    tab_reception, tab_tickets = st.tabs(["🛎️ Reception & Kiosk", "🎫 My Support & Escalation Tickets"])
    tab_records = None


# =========================================================
# TAB 1: RECEPTION LOBBY & INTERACTIVE CHATBOT KIOSK
# =========================================================
with tab_reception:

    # -----------------------------------------------------
    # SCENE 1: THE COLLEGE RECEPTION AREA (LOBBY VIEW)
    # -----------------------------------------------------
    if st.session_state.reception_mode == "lobby":

        col_desk, col_actions = st.columns([1.5, 1])

        with col_desk:
            st.markdown(
                f"""
                <div class="desk-hero-card">
                    <div class="receptionist-avatar-frame">
                        <div class="receptionist-avatar-img">👩‍💼</div>
                        <div class="avatar-status-dot"></div>
                    </div>
                    <div style="flex:1;">
                        <div class="desk-nameplate">
                            <span>Official Reception Desk • Counter 01</span>
                        </div>
                        <h2 class="receptionist-name">Aussie • AI Campus Receptionist</h2>
                        <div class="receptionist-dialogue">
                            "Good evening, <strong>{curr_user.name}</strong>! Welcome to Bosscoder College Student Center. I'm Aussie, your front desk concierge. 
                            Step up to my desk or ring the service bell to inquire about academic policies, library hours, 
                            hostel rules, fee submissions, or lost items. I'll open up the interactive inquiry terminal for you!"
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_actions:
            st.markdown(
                """
                <div style="background:#FFFFFF; border:1px solid rgba(104, 66, 194, 0.15); border-radius:22px; padding:22px; box-shadow:0 8px 24px rgba(33, 19, 61, 0.05);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <span style="font-size:0.8rem; font-weight:800; color:#6842C2; text-transform:uppercase; letter-spacing:1px;">
                            Front Desk Actions
                        </span>
                        <div class="ai-assistant-indicator">
                            <span class="ai-orb-core"></span>
                            <span>Aussie Ready</span>
                        </div>
                    </div>
                    <p style="font-size:0.86rem; color:#64557E; margin-bottom:18px; line-height:1.45;">
                        Ring the service bell or step directly up to Aussie's desk to start your inquiry session.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("🛎️ Ring Desk Bell", use_container_width=True, type="primary"):
                    st.session_state.bell_count += 1
                    render_bell_chime_trigger()
                    st.toast("🛎️ *Ding!* Aussie smiles: 'Welcome Serina! How can I help you today?'")
                    time.sleep(0.4)
            with col_b2:
                if st.button("🚶 Step Up to Desk", use_container_width=True):
                    render_bell_chime_trigger()
                    st.session_state.reception_mode = "kiosk"
                    st.rerun()

            st.markdown(
                f"""
                <div style="text-align:center; margin-top:14px; font-size:0.8rem; color:#64557E;">
                    Desk bell rung <strong style="color:#21133D;">{st.session_state.bell_count}</strong> time(s) today.
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 🗂️ Front Desk Quick Brochures & Department Trays")
        st.caption("Click any campus topic below to approach Aussie with that inquiry:")

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📚 Central Library Hours & Study Cubicles", use_container_width=True):
                st.session_state.pending_query = "What are the Central Library operating hours and study cubicle rules?"
                st.session_state.reception_mode = "kiosk"
                render_bell_chime_trigger()
                st.rerun()

            if st.button("📌 Minimum Attendance & Condonation Policy", use_container_width=True):
                st.session_state.pending_query = "What is the minimum attendance requirement and the policy for medical condonation?"
                st.session_state.reception_mode = "kiosk"
                render_bell_chime_trigger()
                st.rerun()

        with c2:
            if st.button("📍 Finance & Fees Office Location", use_container_width=True):
                st.session_state.pending_query = "Where is the finance and accounts office located and when is it open?"
                st.session_state.reception_mode = "kiosk"
                render_bell_chime_trigger()
                st.rerun()

            if st.button("🚪 Hostel Curfew Timings & Outing Passes", use_container_width=True):
                st.session_state.pending_query = "What are the hostel curfew timings, late entry rules, and weekend outing procedures?"
                st.session_state.reception_mode = "kiosk"
                render_bell_chime_trigger()
                st.rerun()

        with c3:
            if st.button("📝 Grade Appeals & Revaluation Process", use_container_width=True):
                st.session_state.pending_query = "What is the fee and procedure for grade revaluation and photocopy of answer scripts?"
                st.session_state.reception_mode = "kiosk"
                render_bell_chime_trigger()
                st.rerun()

            if st.button("🔍 Lost ID Card Escalation & Helpdesk", use_container_width=True):
                st.session_state.pending_query = "I lost my university student ID card. What should I do to get a replacement?"
                st.session_state.reception_mode = "kiosk"
                render_bell_chime_trigger()
                st.rerun()

    # -----------------------------------------------------
    # SCENE 2: THE INTERACTIVE RECEPTIONIST KIOSK (CHATBOT)
    # -----------------------------------------------------
    else:
        # Kiosk Header with Aussie and "Return to Lobby" action
        col_kh1, col_kh2 = st.columns([3, 1])
        with col_kh1:
            st.markdown(
                f"""
                <div class="kiosk-header">
                    <div class="kiosk-receptionist-info">
                        <div class="kiosk-avatar">👩‍💼</div>
                        <div>
                            <h3 class="kiosk-title">
                                <span>Aussie • AI Campus Receptionist</span>
                                <span class="ai-assistant-indicator" style="background:rgba(214,243,106,0.2); border:1px solid #D6F36A; color:#D6F36A;">
                                    <span class="ai-orb-core"></span> ACTIVE
                                </span>
                            </h3>
                            <span class="kiosk-status">Serving {curr_user.name} • Bosscoder Reception Counter 01</span>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_kh2:
            c_ret, c_ring = st.columns(2)
            with c_ret:
                if st.button("🚪 Lobby", use_container_width=True):
                    st.session_state.reception_mode = "lobby"
                    st.rerun()
            with c_ring:
                if st.button("🛎️ Bell", use_container_width=True):
                    render_bell_chime_trigger()
                    st.toast("🛎️ *Ding!* Aussie is ready for your inquiry!")

        # Suggested prompt chips inside the kiosk
        st.markdown("##### 💡 Frequently Asked Campus Questions:")
        chip_col1, chip_col2, chip_col3 = st.columns(3)
        quick_query = None

        with chip_col1:
            if st.button("📌 Attendance Rules", use_container_width=True):
                quick_query = "What is the minimum attendance requirement?"
            if st.button("📚 Library Hours", use_container_width=True):
                quick_query = "What are the Central Library operating hours?"

        with chip_col2:
            if st.button("📍 Finance Office Location", use_container_width=True):
                quick_query = "Where is the finance and accounts office located?"
            if st.button("🚪 Hostel Curfew", use_container_width=True):
                quick_query = "What are the hostel curfew timings?"

        with chip_col3:
            if st.button("📝 Grade Revaluation Fee", use_container_width=True):
                quick_query = "What is the fee and procedure for grade revaluation?"
            if st.button("🔍 Lost ID Card", use_container_width=True):
                quick_query = "I lost my university student ID card. What should I do?"

        st.markdown("---")

        # Render conversation history (White Rounded Cards)
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(f"**{curr_user.name}:** {msg['content']}")
            else:
                with st.chat_message("assistant", avatar="👩‍💼"):
                    st.markdown(
                        """
                        <div class="official-seal-tag">
                            <span>🏛️ Bosscoder College Verified Records</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.markdown(msg["content"])

                    if msg.get("latency"):
                        lat = msg["latency"]
                        st.markdown(
                            f"""
                            <div>
                                <span class="metric-pill">⚡ Vector Embed: <strong>{lat['embed']:.3f}s</strong></span>
                                <span class="metric-pill">🔍 Search: <strong>{lat['retrieval']:.3f}s</strong></span>
                                <span class="metric-pill">🧠 Inference: <strong>{lat['gen']:.3f}s</strong></span>
                                <span class="metric-pill">⏱️ Total: <strong>{lat['total']:.3f}s</strong></span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    if msg.get("sources"):
                        with st.expander(f"📑 Consulted Official College Documents ({len(msg['sources'])} records)", expanded=False):
                            for i, src in enumerate(msg["sources"], start=1):
                                sim = src.get("similarity", 0.0) * 100
                                doc_name = src.get("metadata", {}).get("source", "Official Handbook")
                                page = src.get("metadata", {}).get("page", 1)
                                st.markdown(
                                    f"""
                                    <div class="citation-card">
                                        <div class="citation-header">
                                            <span>📄 Source {i}: {doc_name} (Section/Page {page})</span>
                                            <span class="citation-badge">Relevance: {sim:.1f}%</span>
                                        </div>
                                        <div style="font-size:0.84rem; color:#64557E; line-height:1.45;">{src.get("text", "")}</div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )

        # Input box
        user_query = st.chat_input("Ask Aussie about Bosscoder College regulations, library timings, fees, or lost items...")

        # Determine which query to execute
        active_query = st.session_state.pending_query or quick_query or user_query
        if st.session_state.pending_query:
            st.session_state.pending_query = None

        if active_query:
            st.session_state.messages.append({"role": "user", "content": active_query})
            with st.chat_message("user"):
                st.markdown(f"**{curr_user.name}:** {active_query}")

            with st.chat_message("assistant", avatar="👩‍💼"):
                with st.spinner("Aussie is consulting Bosscoder College policy records..."):
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

                    st.markdown(
                        """
                        <div class="official-seal-tag">
                            <span>🏛️ Bosscoder College Verified Records</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.markdown(res["text"])

                    st.markdown(
                        f"""
                        <div>
                            <span class="metric-pill">⚡ Vector Embed: <strong>{emb_t:.3f}s</strong></span>
                            <span class="metric-pill">🔍 Search: <strong>{ret_t:.3f}s</strong></span>
                            <span class="metric-pill">🧠 Inference: <strong>{res['latency']:.3f}s</strong></span>
                            <span class="metric-pill">⏱️ Total: <strong>{total_t:.3f}s</strong></span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Automated Escalation Intent Detection & Ticket Modal
                    detected_category = ticketing.detect_escalation_intent(active_query)
                    if detected_category or not confidence_info["is_confident"]:
                        cat_name = detected_category or "Administrative Inquiry"
                        st.markdown(
                            f"""
                            <div class="escalation-box">
                                <strong>🛎️ Receptionist Escalation Desk:</strong><br>
                                Aussie notes that your inquiry relates to <strong>{cat_name}</strong>. If institutional documentation does not fully resolve this matter, Aussie can dispatch an official administrative support ticket immediately.
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        with st.expander(f"🎫 Open Official {cat_name} Ticket at Reception Desk", expanded=True):
                            with st.form(f"ticket_kiosk_{int(time.time())}"):
                                t_title = st.text_input("Inquiry Summary", value=f"Inquiry: {active_query[:50]}")
                                t_desc = st.text_area("Detailed Details / Identifiers", value=f"Visitor query: {active_query}")
                                t_prio = st.selectbox("Priority Level", ["Medium", "High", "Critical", "Low"])
                                if st.form_submit_button("Submit Ticket to Department Admin"):
                                    created = ticketing.create_ticket(
                                        user_email=curr_user.email,
                                        user_name=curr_user.name,
                                        category=cat_name,
                                        title=t_title,
                                        description=t_desc,
                                        priority=t_prio,
                                    )
                                    st.success(f"Ticket {created.ticket_number} logged! Aussie has forwarded it to the {cat_name} administrator.")

                    if hits:
                        with st.expander(f"📑 Consulted Official College Documents ({len(hits)} records)", expanded=True):
                            for i, src in enumerate(hits, start=1):
                                sim = src.get("similarity", 0.0) * 100
                                doc_name = src.get("metadata", {}).get("source", "Official Handbook")
                                page = src.get("metadata", {}).get("page", 1)
                                st.markdown(
                                    f"""
                                    <div class="citation-card">
                                        <div class="citation-header">
                                            <span>📄 Source {i}: {doc_name} (Section/Page {page})</span>
                                            <span class="citation-badge">Relevance: {sim:.1f}%</span>
                                        </div>
                                        <div style="font-size:0.84rem; color:#64557E; line-height:1.45;">{src.get("text", "")}</div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )


# =========================================================
# TAB 2: SUPPORT TICKETS & ADMINISTRATIVE TRIAGE
# =========================================================
with tab_tickets:
    if curr_user.is_admin:
        st.subheader("📋 Administrative Reception & Escalation Desk")
        st.caption("Review, triage, and resolve student inquiries escalated by Aussie from the front desk.")

        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            status_filter = st.selectbox("Filter by Status", ["All", "Open", "In Review", "Resolved", "Closed"])
        with col_f2:
            st.metric("Total Received Tickets", len(ticketing.get_all_tickets()))

        all_tickets = ticketing.get_all_tickets(status_filter=status_filter)
        if not all_tickets:
            st.info("No tickets currently match this status filter.")
        else:
            for t in all_tickets:
                with st.expander(f"[{t.ticket_number}] {t.category}: {t.title} ({t.status}) • Priority: {t.priority}"):
                    st.write(f"**Submitted By:** {t.user_name} ({t.user_email})")
                    st.write(f"**Logged Date:** {t.created_at}")
                    st.write(f"**Description:** {t.description}")
                    if t.admin_notes:
                        st.info(f"**Admin Remarks:** {t.admin_notes}")

                    with st.form(f"update_ticket_{t.id}"):
                        c_u1, c_u2 = st.columns([1, 2])
                        with c_u1:
                            new_st = st.selectbox(
                                "Update Status",
                                ["Open", "In Review", "Resolved", "Closed"],
                                index=["Open", "In Review", "Resolved", "Closed"].index(t.status),
                            )
                        with c_u2:
                            new_notes = st.text_input("Official Resolution Remarks", value=t.admin_notes or "")

                        if st.form_submit_button("Save Resolution"):
                            ticketing.update_ticket_status(t.id, new_st, new_notes)
                            st.success(f"Ticket {t.ticket_number} updated to {new_st}!")
                            time.sleep(0.4)
                            st.rerun()

    else:
        st.subheader("🎫 My Front Desk Support & Escalation Tickets")
        st.caption("Track the status of inquiries or claims filed with Aussie at the reception desk.")

        with st.expander("➕ Open a New Department Ticket with Aussie", expanded=False):
            with st.form("manual_ticket_form"):
                cat = st.selectbox(
                    "Department Category",
                    ["Lost & Found", "Hostel Maintenance", "Academic Escalation", "Fee Grievance", "General Admin"],
                )
                title = st.text_input("Summary Title", placeholder="e.g. Lost Laptop Charger in Central Library 2nd Floor")
                desc = st.text_area("Detailed Description", placeholder="Specify location, date, time, and identifying marks...")
                prio = st.selectbox("Priority Level", ["Low", "Medium", "High", "Critical"], index=1)
                if st.form_submit_button("Submit to Receptionist"):
                    if title and desc:
                        t = ticketing.create_ticket(
                            user_email=curr_user.email,
                            user_name=curr_user.name,
                            category=cat,
                            title=title,
                            description=desc,
                            priority=prio,
                        )
                        st.success(f"Ticket {t.ticket_number} created! Aussie has queued it for administrative review.")
                        time.sleep(0.4)
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
                    st.write(f"**Submitted Date:** {t.created_at}")
                    st.write(f"**Priority:** {t.priority}")
                    st.write(f"**Details:** {t.description}")
                    if t.admin_notes:
                        st.success(f"**Official Administrative Resolution:** {t.admin_notes}")
                    else:
                        st.caption("Awaiting administrative review.")


# =========================================================
# TAB 3: KNOWLEDGE BASE & CAMPUS DIRECTORY (ADMIN ONLY)
# =========================================================
if curr_user.is_admin and tab_records:
    with tab_records:
        st.subheader("📊 Knowledge Base & System Telemetry")
        st.caption("Administrative oversight over official university repositories and vector embeddings.")

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Indexed RAG Chunks", store.count())
        col_m2.metric("Active Collection", store.collection_name)
        col_m3.metric("SQLite DB Status", "Connected (data/db/campus.db)")

        st.markdown("#### Official Policy Handbooks")
        docs = list(SAMPLE_DOCS_DIR.glob("*.*"))
        for d in docs:
            st.write(f"📄 `{d.name}` ({d.stat().st_size} bytes)")
