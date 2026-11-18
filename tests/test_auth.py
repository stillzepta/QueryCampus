import pytest
from src.auth import authenticate_user, get_demo_user, User

def test_student_authentication():
    user = authenticate_user("student@pesu.pes.edu", "password123")
    assert user is not None
    assert user.role == "student"
    assert user.is_student is True
    assert user.is_admin is False
    assert user.id_number == "PES2UG22CS001"

def test_admin_authentication():
    user = authenticate_user("admin@pesu.pes.edu", "adminpassword")
    assert user is not None
    assert user.role == "admin"
    assert user.is_admin is True
    assert user.is_student is False

def test_invalid_authentication():
    assert authenticate_user("unknown@pesu.pes.edu", "wrong") is None
    assert authenticate_user("student@pesu.pes.edu", "wrongpassword") is None

def test_demo_user_helper():
    student = get_demo_user("student")
    assert student.is_student is True
    admin = get_demo_user("admin")
    assert admin.is_admin is True
