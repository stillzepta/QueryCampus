"""
Institutional Authentication & Role-Based Access Control (RBAC).
Provides mock authentication for PES University institutional users,
supporting Student and Administrator roles.
"""

from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class User:
    email: str
    name: str
    role: str  # "student" or "admin"
    department: str
    id_number: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_student(self) -> bool:
        return self.role == "student"


# Pre-configured institutional mock users for easy demonstration
MOCK_USERS: Dict[str, Dict[str, str]] = {
    "student@pesu.pes.edu": {
        "password": "password123",
        "name": "Alex Sharma",
        "role": "student",
        "department": "Computer Science & Engineering",
        "id_number": "PES2UG22CS001",
    },
    "admin@pesu.pes.edu": {
        "password": "adminpassword",
        "name": "Dr. V. Ramanathan (Registrar Desk)",
        "role": "admin",
        "department": "Office of Academic Affairs & Administration",
        "id_number": "ADM-PES-042",
    },
    "guest@pesu.pes.edu": {
        "password": "guest",
        "name": "Campus Visitor",
        "role": "student",
        "department": "General Inquiries",
        "id_number": "VIS-2026-99",
    },
}


def authenticate_user(identifier: str, password: str) -> Optional[User]:
    """
    Verifies user credentials against institutional directory.
    Returns User object on success, None on failure.
    """
    cleaned_id = identifier.strip().lower()
    user_data = MOCK_USERS.get(cleaned_id)
    if not user_data:
        return None

    if user_data["password"] == password:
        return User(
            email=cleaned_id,
            name=user_data["name"],
            role=user_data["role"],
            department=user_data["department"],
            id_number=user_data["id_number"],
        )
    return None


def get_demo_user(role: str = "student") -> User:
    """Convenience helper to retrieve default student or admin user."""
    if role == "admin":
        data = MOCK_USERS["admin@pesu.pes.edu"]
        email = "admin@pesu.pes.edu"
    else:
        data = MOCK_USERS["student@pesu.pes.edu"]
        email = "student@pesu.pes.edu"

    return User(
        email=email,
        name=data["name"],
        role=data["role"],
        department=data["department"],
        id_number=data["id_number"],
    )
