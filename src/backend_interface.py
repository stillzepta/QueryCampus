"""
Backend Interface Facade for Frontend Integration.
Module: src/backend_interface.py
Author: Krishna Verma (LLM & Backend Integrator)

Provides a clean, unified contract for Sachita's Streamlit frontend (frontend/app.py).
Encapsulates all internal ChromaDB, Ollama/Groq routing, vision parsing, and SQLite ticketing logic.
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.retrieval import retrieve_context, CampusRetriever, CONFIDENCE_THRESHOLD
from src.generator import CampusGenerator
from src.ticketing import TicketingSystem, Ticket


# Singleton backend instances
_generator = CampusGenerator()
_ticketing = TicketingSystem()


def _format_history_list(chat_history: Optional[List[Dict[str, str]]]) -> str:
    """Formats chat history array into formatted dialogue string."""
    if not chat_history:
        return ""
    lines = []
    # Use only last 6 messages (3 turns)
    recent = chat_history[-6:]
    for msg in recent:
        role = msg.get("role", "user")
        content = msg.get("content", "").strip()
        speaker = "Student" if role == "user" else "QueryCampus Receptionist"
        lines.append(f"{speaker}: {content}")
    return "\n".join(lines)


def process_student_turn(
    query: str,
    user_session: Dict[str, Any],
    chat_history: Optional[List[Dict[str, str]]] = None,
    inference_mode: str = "groq",
    uploaded_image: Optional[bytes] = None,
) -> Dict[str, Any]:
    """
    Primary orchestrator for a single student turn.
    Guarantees the following return schema:
    {
      "answer": str,
      "latency_ms": float,
      "mode_used": str,
      "confidence_score": float,
      "citations": [{"source": str, "page": int, "section": str, "snippet": str}],
      "requires_ticket": bool,
      "ticket_draft": {"category": str, "summary": str, "query_text": str} | None
    }
    """
    t_start = time.perf_counter()
    clean_query = query.strip()

    # Step 1: Multi-modal Vision Parsing (Notice board, map, schedule)
    visual_text: Optional[str] = None
    search_query = clean_query

    if uploaded_image:
        vision_result = _generator.analyze_campus_image(
            image_bytes=uploaded_image,
            user_query=clean_query,
            mode=inference_mode,
        )
        visual_text = vision_result.get("extracted_text", "")
        if visual_text and not visual_text.startswith("[Notice Board Image Analyzed:"):
            # Augment query for vector retrieval
            search_query = f"{clean_query} {visual_text[:120]}"

    # Step 2: Context Retrieval & Confidence Scoring
    retrieval_res = retrieve_context(query=search_query, top_k=3)
    chunks = retrieval_res.get("chunks", [])
    confidence_score = float(retrieval_res.get("max_score", 0.0))
    is_confident = bool(retrieval_res.get("is_confident", False))
    formatted_context = retrieval_res.get("formatted_context", "")

    # Step 3: Escalation & Ticket Intent Detection
    detected_category = _ticketing.detect_escalation_intent(clean_query)
    requires_ticket = (detected_category is not None) or (not is_confident)

    ticket_draft: Optional[Dict[str, str]] = None
    if requires_ticket:
        cat = detected_category or "Administrative Inquiry"
        ticket_draft = {
            "category": cat,
            "summary": f"Inquiry: {clean_query[:50]}",
            "query_text": clean_query,
        }

    # Step 4: Strict LLM Generation
    history_str = _format_history_list(chat_history)
    use_groq = inference_mode.lower() == "groq"

    gen_res = _generator.generate(
        query=clean_query,
        context=formatted_context,
        history_str=history_str,
        visual_notice_text=visual_text,
        use_groq=use_groq,
    )

    answer_text = gen_res.get("text", "")
    provider = gen_res.get("provider", "LLM Engine")
    model_name = gen_res.get("model", "default")
    mode_used = f"{provider} ({model_name})"

    # Step 5: Format Citations
    citations: List[Dict[str, Any]] = []
    for c in chunks:
        citations.append(
            {
                "source": c.get("source", "Campus Document"),
                "page": int(c.get("page", 1)),
                "section": c.get("section", "General"),
                "snippet": c.get("text", "").strip(),
            }
        )

    # Step 6: Compute Total Latency in Milliseconds
    latency_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

    return {
        "answer": answer_text,
        "latency_ms": latency_ms,
        "mode_used": mode_used,
        "confidence_score": confidence_score,
        "citations": citations,
        "requires_ticket": requires_ticket,
        "ticket_draft": ticket_draft,
    }


def create_escalation_ticket(
    ticket_data: Dict[str, str],
    user_session: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Submits an official ticket to SQLite (data/db/querycampus.db).
    """
    user_email = user_session.get("email", "student@pesu.pes.edu")
    user_name = user_session.get("name", "Student User")
    category = ticket_data.get("category", "General Escalation")
    title = ticket_data.get("summary") or ticket_data.get("title", "Support Request")
    desc = ticket_data.get("query_text") or ticket_data.get("description", "Details pending.")
    priority = ticket_data.get("priority", "Medium")

    ticket = _ticketing.create_ticket(
        user_email=user_email,
        user_name=user_name,
        category=category,
        title=title,
        description=desc,
        priority=priority,
    )

    return {
        "ticket_id": ticket.id,
        "ticket_number": ticket.ticket_number,
        "status": ticket.status,
        "created_at": ticket.created_at,
        "success": True,
    }


def get_student_tickets(user_email: str) -> List[Dict[str, Any]]:
    """Retrieves all tickets submitted by a student."""
    tickets = _ticketing.get_user_tickets(user_email)
    return [
        {
            "id": t.id,
            "ticket_number": t.ticket_number,
            "category": t.category,
            "title": t.title,
            "description": t.description,
            "status": t.status,
            "priority": t.priority,
            "created_at": t.created_at,
            "admin_notes": t.admin_notes,
        }
        for t in tickets
    ]


def get_admin_tickets(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all tickets for the Administrator dashboard."""
    tickets = _ticketing.get_all_tickets(status_filter=status_filter)
    return [
        {
            "id": t.id,
            "ticket_number": t.ticket_number,
            "user_name": t.user_name,
            "user_email": t.user_email,
            "category": t.category,
            "title": t.title,
            "description": t.description,
            "status": t.status,
            "priority": t.priority,
            "created_at": t.created_at,
            "admin_notes": t.admin_notes,
        }
        for t in tickets
    ]


def update_admin_ticket(ticket_id: int, new_status: str, admin_notes: Optional[str] = None) -> bool:
    """Updates ticket status and official administrative remarks."""
    return _ticketing.update_ticket_status(ticket_id, new_status, admin_notes)
