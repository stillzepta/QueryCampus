import base64
import pytest
from src.backend_interface import (
    process_student_turn,
    create_escalation_ticket,
    get_student_tickets,
)

def test_process_student_turn_schema():
    session = {"name": "Alex Sharma", "email": "student@pesu.pes.edu", "role": "student"}
    result = process_student_turn(
        query="What is the minimum attendance requirement?",
        user_session=session,
        chat_history=[],
        inference_mode="ollama",
    )

    # Validate guaranteed schema
    expected_keys = {
        "answer",
        "latency_ms",
        "mode_used",
        "confidence_score",
        "citations",
        "requires_ticket",
        "ticket_draft",
    }
    assert expected_keys.issubset(set(result.keys()))
    assert isinstance(result["answer"], str)
    assert isinstance(result["latency_ms"], float)
    assert isinstance(result["confidence_score"], float)
    assert isinstance(result["citations"], list)
    assert isinstance(result["requires_ticket"], bool)

def test_process_student_turn_lost_item_escalation():
    session = {"name": "Alex Sharma", "email": "student@pesu.pes.edu", "role": "student"}
    result = process_student_turn(
        query="I lost my college ID card near Block A",
        user_session=session,
        chat_history=[],
        inference_mode="ollama",
    )

    assert result["requires_ticket"] is True
    assert result["ticket_draft"] is not None
    assert result["ticket_draft"]["category"] == "Lost & Found"

    # Test ticket creation from draft
    ticket_res = create_escalation_ticket(result["ticket_draft"], user_session=session)
    assert ticket_res["success"] is True
    assert ticket_res["ticket_number"].startswith("QC-")

    # Verify retrieval
    user_tickets = get_student_tickets("student@pesu.pes.edu")
    assert any(t["ticket_number"] == ticket_res["ticket_number"] for t in user_tickets)
