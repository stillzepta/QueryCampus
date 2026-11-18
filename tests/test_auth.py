import os
import tempfile
from pathlib import Path
import pytest

from src.auth import (
    authenticate_user,
    get_demo_user,
    get_judge_switcher_options,
    User,
    init_auth_db,
    init_user_session,
    is_valid_institutional_domain,
    validate_institutional_email,
    validate_usn,
    verify_role,
    require_role,
    register_user,
    create_session,
    validate_session,
    invalidate_session,
    get_supabase_client,
    Role,
    DEFAULT_STUDENT_SESSION,
    DEFAULT_ADMIN_SESSION,
)
from src.ticketing import TicketingSystem
from src.backend_interface import get_admin_tickets, update_admin_ticket


def test_student_authentication():
    user = authenticate_user("student@pesu.pes.edu", "password123")
    assert user is not None
    assert user.role == "student"
    assert user.is_student is True
    assert user.is_admin is False
    assert user.id_number == "PES2UG22CS001"
    assert user.usn == "PES2UG22CS001"


def test_admin_authentication():
    user = authenticate_user("admin@pesu.pes.edu", "adminpassword")
    assert user is not None
    assert user.role == "admin"
    assert user.is_admin is True
    assert user.is_student is False
    assert user.id_number == "ADM-PES-042"


def test_invalid_authentication():
    assert authenticate_user("unknown@pesu.pes.edu", "wrong") is None
    assert authenticate_user("student@pesu.pes.edu", "wrongpassword") is None


def test_demo_user_helper():
    student = get_demo_user("student")
    assert student.is_student is True
    admin = get_demo_user("admin")
    assert admin.is_admin is True
    visitor = get_demo_user("visitor")
    assert visitor.role == "student"


def test_judge_switcher_options():
    options = get_judge_switcher_options()
    assert len(options) >= 3
    keys = [opt["key"] for opt in options]
    assert "student" in keys
    assert "admin" in keys


def test_default_student_session():
    sess = init_user_session()
    assert sess["name"] == "Aarav Sharma"
    assert sess["usn"] == "1MS26CS042"
    assert sess["email"] == "aarav.cs26@university.edu"
    assert sess["role"] == "Student"
    assert sess["verified"] is True


def test_domain_validation():
    assert is_valid_institutional_domain("student@university.edu") is True
    assert is_valid_institutional_domain("faculty@college.ac.in") is True
    assert is_valid_institutional_domain("admin@university.org") is True
    assert is_valid_institutional_domain("alex@pesu.pes.edu") is True
    assert is_valid_institutional_domain("registrar@pes.edu") is True
    assert is_valid_institutional_domain("hacker@gmail.com") is False
    assert is_valid_institutional_domain("user@yahoo.co.in") is False
    assert validate_institutional_email("student@university.edu") is True


def test_usn_validation():
    assert validate_usn("PES2UG22CS001") is True
    assert validate_usn("1MS26CS042") is True
    assert validate_usn("ADM-PES-042") is True
    assert validate_usn("") is False
    assert validate_usn("abc") is False


def test_init_auth_db_and_seeding():
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_db = Path(tmp_dir) / "test_auth.db"
        conn = init_auth_db(test_db)
        cursor = conn.cursor()

        # Check users table
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        assert user_count >= 4

        # Check user_sessions table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_sessions'")
        assert cursor.fetchone() is not None


def test_rbac_verification_and_enforcement():
    student_sess = dict(DEFAULT_STUDENT_SESSION)
    admin_sess = dict(DEFAULT_ADMIN_SESSION)

    # Student verification
    assert verify_role(student_sess, "Student") is True
    assert verify_role(student_sess, "Admin") is False

    # Admin verification (Admin satisfies both)
    assert verify_role(admin_sess, "Admin") is True
    assert verify_role(admin_sess, "Student") is True

    # require_role enforcement
    require_role(admin_sess, "Admin")
    require_role(student_sess, "Student")

    with pytest.raises(PermissionError) as exc_info:
        require_role(student_sess, "Admin")
    assert "Requires 'Admin' privileges" in str(exc_info.value)


def test_session_lifecycle():
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_db = Path(tmp_dir) / "test_sessions.db"
        user = get_demo_user("student")

        # Create session
        session_id = create_session(user, db_path=test_db)
        assert session_id is not None
        assert len(session_id) >= 16

        # Validate active session
        validated_user = validate_session(session_id, db_path=test_db)
        assert validated_user is not None
        assert validated_user.email == user.email
        assert validated_user.usn == user.usn

        # Invalidate session
        assert invalidate_session(session_id, db_path=test_db) is True
        assert validate_session(session_id, db_path=test_db) is None


def test_user_registration():
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_db = Path(tmp_dir) / "test_reg.db"

        # Successful registration
        new_user = register_user(
            usn="PES2UG23CS999",
            name="Rohan Gupta",
            email="rohan.gupta@pesu.pes.edu",
            department="CSE",
            semester="4th Semester",
            role="Student",
            db_path=test_db,
        )
        assert new_user.usn == "PES2UG23CS999"
        assert new_user.name == "Rohan Gupta"

        # Invalid domain rejection
        with pytest.raises(ValueError) as exc_info:
            register_user(
                usn="PES2UG23CS998",
                name="Imposter",
                email="imposter@external.com",
                department="CSE",
                db_path=test_db,
            )
        assert "Invalid email domain" in str(exc_info.value)


def test_supabase_cloud_connection():
    client = get_supabase_client()
    if client is not None:
        res = client.table("users").select("usn, name, email, role").execute()
        assert res.data is not None
        assert len(res.data) > 0
        emails = [u["email"] for u in res.data]
        assert "student@pesu.pes.edu" in emails or "aarav.cs26@university.edu" in emails


def test_ticketing_rbac_security():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_ticketing_rbac.db"
        system = TicketingSystem(db_path=db_path)

        ticket = system.create_ticket(
            user_email="student@pesu.pes.edu",
            user_name="Alex Sharma",
            category="Lost & Found",
            title="Lost Smart Watch",
            description="Lost in campus cafeteria",
            user_session=DEFAULT_STUDENT_SESSION,
        )
        assert ticket.ticket_number.startswith("QC-")

        # Student cannot view all admin tickets
        with pytest.raises(PermissionError):
            system.get_all_tickets(user_session=DEFAULT_STUDENT_SESSION)

        # Admin CAN view all admin tickets
        all_tickets = system.get_all_tickets(user_session=DEFAULT_ADMIN_SESSION)
        assert len(all_tickets) >= 1

        # Student cannot update ticket status
        with pytest.raises(PermissionError):
            system.update_ticket_status(
                ticket_id=ticket.id,
                new_status="Resolved",
                user_session=DEFAULT_STUDENT_SESSION,
            )

        # Admin CAN update ticket status
        success = system.update_ticket_status(
            ticket_id=ticket.id,
            new_status="Resolved",
            admin_notes="Returned to student at helpdesk.",
            user_session=DEFAULT_ADMIN_SESSION,
        )
        assert success is True


def test_backend_interface_rbac():
    # Calling get_admin_tickets with student session must raise PermissionError
    with pytest.raises(PermissionError):
        get_admin_tickets(user_session=DEFAULT_STUDENT_SESSION)

    # Calling update_admin_ticket with student session must raise PermissionError
    with pytest.raises(PermissionError):
        update_admin_ticket(ticket_id=1, new_status="Closed", user_session=DEFAULT_STUDENT_SESSION)

    # Calling get_admin_tickets with admin session succeeds
    admin_tickets = get_admin_tickets(user_session=DEFAULT_ADMIN_SESSION)
    assert isinstance(admin_tickets, list)
