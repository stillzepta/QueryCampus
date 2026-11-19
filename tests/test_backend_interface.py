import base64
import pytest
from src.backend_interface import (
    process_student_turn,
    create_escalation_ticket,
    get_student_tickets,
    get_admin_tickets,
    update_admin_ticket,
    list_admin_documents,
    ingest_admin_document,
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


def test_list_admin_documents():
    docs = list_admin_documents()
    assert isinstance(docs, list)
    assert len(docs) >= 1
    # Official 2026 rulebook must be in the active documents
    filenames = [d["filename"] for d in docs]
    assert any("bosscoder_official_2026_rulebook" in fn for fn in filenames)


def test_ingest_admin_document_rbac_and_execution():
    admin_sess = {"name": "Krishna Verma", "email": "krishna@bst.edu.in", "role": "Admin"}
    student_sess = {"name": "Amanat Singh", "email": "amanat@bst.edu.in", "role": "Student"}

    sample_content = b"Official Circular 2026: Laboratory timings are extended until 8:00 PM for project teams."

    # Non-admin should be rejected with PermissionError
    with pytest.raises(PermissionError):
        ingest_admin_document(
            filename="test_circular_2026.txt",
            file_bytes=sample_content,
            user_session=student_sess,
        )

    # Admin should succeed
    try:
        res = ingest_admin_document(
            filename="test_circular_2026.txt",
            file_bytes=sample_content,
            user_session=admin_sess,
        )
        assert res["success"] is True
        assert res["chunks_added"] >= 1
        assert "test_circular_2026.txt" in res["filename"]
    finally:
        from pathlib import Path
        import os
        target_dir = Path(os.getenv("SAMPLE_DOCS_DIR", "./data/sample_docs"))
        test_file = target_dir / "test_circular_2026.txt"
        if test_file.exists():
            test_file.unlink()


def test_admin_ticket_lifecycle_and_rbac():
    admin_sess = {"name": "Krishna Verma", "email": "krishna@bst.edu.in", "role": "Admin"}
    student_sess = {"name": "Amanat Singh", "email": "amanat@bst.edu.in", "role": "Student"}

    # Fetch admin tickets
    tickets = get_admin_tickets(user_session=admin_sess)
    assert isinstance(tickets, list)
    assert len(tickets) >= 1

    first_ticket_id = tickets[0]["id"]

    # Student cannot call admin ticket update
    with pytest.raises(PermissionError):
        update_admin_ticket(
            ticket_id=first_ticket_id,
            new_status="Resolved",
            admin_notes="Unauthorized attempt",
            user_session=student_sess,
        )

    # Admin updates ticket
    success = update_admin_ticket(
        ticket_id=first_ticket_id,
        new_status="In Review",
        admin_notes="Security desk notified to check CCTV footage.",
        user_session=admin_sess,
    )
    assert success is True
