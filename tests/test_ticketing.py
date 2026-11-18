import tempfile
from pathlib import Path
import pytest
from src.ticketing import TicketingSystem

@pytest.fixture
def temp_ticketing():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_campus.db"
        system = TicketingSystem(db_path=db_path)
        yield system

def test_create_and_fetch_ticket(temp_ticketing):
    ticket = temp_ticketing.create_ticket(
        user_email="student@pesu.pes.edu",
        user_name="Alex Sharma",
        category="Lost & Found",
        title="Lost ID Badge",
        description="Left badge in Block A Room 102",
        priority="High",
    )
    assert ticket.id is not None
    assert ticket.ticket_number.startswith("QC-")
    assert ticket.status == "Open"

    user_tickets = temp_ticketing.get_user_tickets("student@pesu.pes.edu")
    assert len(user_tickets) == 1
    assert user_tickets[0].title == "Lost ID Badge"

def test_update_ticket_status(temp_ticketing):
    ticket = temp_ticketing.create_ticket(
        user_email="student@pesu.pes.edu",
        user_name="Alex Sharma",
        category="Hostel Maintenance",
        title="Fan repair",
        description="Fan in Room 302 not rotating",
    )
    updated = temp_ticketing.update_ticket_status(
        ticket_id=ticket.id,
        new_status="Resolved",
        admin_notes="Electrician fixed regulator",
    )
    assert updated is True

    all_tickets = temp_ticketing.get_all_tickets(status_filter="Resolved")
    assert len(all_tickets) == 1
    assert all_tickets[0].admin_notes == "Electrician fixed regulator"

def test_detect_escalation_intent():
    assert TicketingSystem.detect_escalation_intent("I lost my student wallet") == "Lost & Found"
    assert TicketingSystem.detect_escalation_intent("The water tap is broken in hostel") == "Hostel Maintenance"
    assert TicketingSystem.detect_escalation_intent("What is the attendance rule?") is None
