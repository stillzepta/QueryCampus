"""
Institutional Authentication & 1-Click Judge Role Switcher.
Module: src/auth.py
Maintained by: Sachita (Full-Stack & UI/UX Developer)

Provides institutional directory simulation, role-based access control (Student vs. Administrator),
and a 1-click persona switcher designed specifically for hackathon judging and evaluation.
"""

from dataclasses import dataclass
from typing import Optional, Dict, List, Any


@dataclass
class User:
    email: str
    name: str
    role: str  # "student" or "admin"
    department: str
    id_number: str
    badge_label: str = "Student"
    avatar_emoji: str = "🎓"

    @property
    def is_admin(self) -> bool:
        return self.role.lower() == "admin"

    @property
    def is_student(self) -> bool:
        return self.role.lower() == "student"

    def to_session_dict(self) -> Dict[str, Any]:
        return {
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "department": self.department,
            "id_number": self.id_number,
            "badge_label": self.badge_label,
            "avatar_emoji": self.avatar_emoji,
        }


# Pre-configured institutional personas for 1-Click Judge Switching
JUDGE_PERSONAS: Dict[str, Dict[str, Any]] = {
    "student": {
        "email": "student@pesu.pes.edu",
        "password": "password123",
        "name": "Alex Sharma",
        "role": "student",
        "department": "Computer Science & Engineering (B.Tech)",
        "id_number": "PES2UG22CS001",
        "badge_label": "Enrolled Undergraduate",
        "avatar_emoji": "🎓",
        "bio": "3rd-Year student needing attendance policies, exam schedules, and hostel curfew verification.",
    },
    "admin": {
        "email": "admin@pesu.pes.edu",
        "password": "adminpassword",
        "name": "Dr. V. Ramanathan",
        "role": "admin",
        "department": "Office of Academic Affairs & Administration",
        "id_number": "ADM-PES-042",
        "badge_label": "Chief Administrative Officer",
        "avatar_emoji": "🛡️",
        "bio": "Central administrator with full access to support ticket queues, escalation resolution, and knowledge base indexing.",
    },
    "finance_officer": {
        "email": "finance.lead@pesu.pes.edu",
        "password": "financepassword",
        "name": "S. K. Kulkarni (Finance Desk)",
        "role": "admin",
        "department": "Office of the Bursar & Student Accounts (Block A, Room 102)",
        "id_number": "FIN-DESK-102",
        "badge_label": "Finance Officer",
        "avatar_emoji": "💼",
        "bio": "Manages tuition fee clearances, revaluation fee refunds, and student payment grievances.",
    },
    "visitor": {
        "email": "judge.guest@pesu.pes.edu",
        "password": "guestpassword",
        "name": "Hackathon Judge / Campus Visitor",
        "role": "student",
        "department": "Campus Guest & Evaluation Track",
        "id_number": "EVAL-2026-JUDGE",
        "badge_label": "Guest Evaluator",
        "avatar_emoji": "⚖️",
        "bio": "Evaluates zero-hallucination answers, citation cards, and automated ticket escalation in real time.",
    },
}


def authenticate_user(identifier: str, password: str) -> Optional[User]:
    """
    Verifies user credentials against institutional directory.
    Returns User object on success, None on failure.
    """
    cleaned_id = identifier.strip().lower()
    for persona_key, data in JUDGE_PERSONAS.items():
        if data["email"].lower() == cleaned_id and data["password"] == password:
            return User(
                email=data["email"],
                name=data["name"],
                role=data["role"],
                department=data["department"],
                id_number=data["id_number"],
                badge_label=data["badge_label"],
                avatar_emoji=data["avatar_emoji"],
            )
    return None


def get_demo_user(role_or_key: str = "student") -> User:
    """Convenience helper to retrieve default persona for quick demo login."""
    key = role_or_key.lower()
    if key in JUDGE_PERSONAS:
        data = JUDGE_PERSONAS[key]
    elif key == "admin":
        data = JUDGE_PERSONAS["admin"]
    else:
        data = JUDGE_PERSONAS["student"]

    return User(
        email=data["email"],
        name=data["name"],
        role=data["role"],
        department=data["department"],
        id_number=data["id_number"],
        badge_label=data["badge_label"],
        avatar_emoji=data["avatar_emoji"],
    )


def get_judge_switcher_options() -> List[Dict[str, Any]]:
    """Returns all persona options for the 1-click judge role switcher UI."""
    options = []
    for key, val in JUDGE_PERSONAS.items():
        options.append({
            "key": key,
            "label": f"{val['avatar_emoji']} {val['name']} ({val['role'].capitalize()})",
            "role": val["role"],
            "department": val["department"],
            "bio": val["bio"],
        })
    return options
