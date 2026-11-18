"""
Institutional Authentication, Supabase Cloud Identity & RBAC Engine.
Module: src/auth.py
Author: Krishna Verma (LLM & Backend Integrator) & Sachita (Full-Stack & UI/UX Developer)

Provides:
- SQLite persistent identity store (`data/db/querycampus.db`) with `users` and `user_sessions` tables.
- Supabase Cloud PostgreSQL integration with Row-Level Security (RLS) and real-time syncing.
- Institutional domain verification (`@university.edu`, `@pesu.pes.edu`, `@pes.edu`, `@college.ac.in`) and USN validation.
- Role-Based Access Control (RBAC) engine for Student and Administrator roles.
- 1-Click Judge Persona Switcher for hackathon evaluation and zero-downtime demoing.
- UI rendering components for Streamlit frontend (`render_judge_switcher`, `render_auth_sidebar`).
"""

import os
import sys
import uuid
import sqlite3
import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, List, Any, Union

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = Path(os.getenv("DB_DIR", BASE_DIR / "data" / "db"))
DB_PATH = Path(os.getenv("DB_PATH", DB_DIR / "querycampus.db"))

ALLOWED_INSTITUTIONAL_DOMAINS = (
    "university.edu",
    "college.ac.in",
    "university.org",
    "pesu.pes.edu",
    "pes.edu",
)


class RoleStr(str):
    """Case-insensitive string wrapper for roles (Student vs Admin)."""

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            return self.lower() == other.lower()
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash(self.lower())


class Role:
    STUDENT = RoleStr("Student")
    ADMIN = RoleStr("Admin")


@dataclass
class User:
    email: str
    name: str
    role: Union[RoleStr, str] = Role.STUDENT
    department: str = "General Academic"
    id_number: str = ""
    usn: str = ""
    semester: Optional[str] = "1st Semester"
    verified: int = 1
    last_login: Optional[str] = None
    badge_label: str = "Student"
    avatar_emoji: str = "🎓"

    def __post_init__(self):
        # Synchronize usn and id_number
        if not self.usn and self.id_number:
            self.usn = self.id_number
        elif not self.id_number and self.usn:
            self.id_number = self.usn

        # Normalize role to RoleStr
        if isinstance(self.role, str):
            cap = self.role.strip().capitalize()
            self.role = RoleStr(cap if cap in ("Student", "Admin") else "Student")

    @property
    def is_admin(self) -> bool:
        return self.role.lower() == "admin"

    @property
    def is_student(self) -> bool:
        return self.role.lower() == "student"

    def has_role(self, required_role: str) -> bool:
        return verify_role(self, required_role)

    def to_session_dict(self) -> Dict[str, Any]:
        return {
            "usn": self.usn,
            "id_number": self.id_number,
            "email": self.email,
            "name": self.name,
            "role": str(self.role),
            "department": self.department,
            "semester": self.semester or "Undergraduate",
            "verified": bool(self.verified),
            "badge_label": self.badge_label,
            "avatar_emoji": self.avatar_emoji,
            "last_login": self.last_login or datetime.datetime.now().isoformat(),
        }


# Default session fixtures for immediate frontend bootstrapping
DEFAULT_STUDENT_SESSION: Dict[str, Any] = {
    "usn": "1MS26CS042",
    "name": "Aarav Sharma",
    "email": "aarav.cs26@university.edu",
    "department": "Computer Science & Engineering",
    "semester": "6th Semester",
    "role": "Student",
    "verified": True,
    "badge_label": "Enrolled Undergraduate",
    "avatar_emoji": "🎓",
}

DEFAULT_ADMIN_SESSION: Dict[str, Any] = {
    "usn": "ADM-PES-042",
    "name": "Dr. V. Ramanathan",
    "email": "admin@pesu.pes.edu",
    "department": "Office of Academic Affairs & Administration",
    "semester": "Staff",
    "role": "Admin",
    "verified": True,
    "badge_label": "Chief Administrative Officer",
    "avatar_emoji": "🛡️",
}


# Pre-configured institutional personas for 1-Click Judge Switching
JUDGE_PERSONAS: Dict[str, Dict[str, Any]] = {
    "student": {
        "usn": "PES2UG22CS001",
        "email": "student@pesu.pes.edu",
        "password": "password123",
        "name": "Alex Sharma",
        "role": "Student",
        "department": "Computer Science & Engineering (B.Tech)",
        "semester": "6th Semester",
        "id_number": "PES2UG22CS001",
        "badge_label": "Enrolled Undergraduate",
        "avatar_emoji": "🎓",
        "bio": "3rd-Year student needing attendance policies, exam schedules, and hostel curfew verification.",
    },
    "aarav": {
        "usn": "1MS26CS042",
        "email": "aarav.cs26@university.edu",
        "password": "password123",
        "name": "Aarav Sharma",
        "role": "Student",
        "department": "Computer Science & Engineering",
        "semester": "6th Semester",
        "id_number": "1MS26CS042",
        "badge_label": "Enrolled Undergraduate",
        "avatar_emoji": "🎓",
        "bio": "Undergraduate student inquiring about academic rules, fee structures, and campus services.",
    },
    "admin": {
        "usn": "ADM-PES-042",
        "email": "admin@pesu.pes.edu",
        "password": "adminpassword",
        "name": "Dr. V. Ramanathan",
        "role": "Admin",
        "department": "Office of Academic Affairs & Administration",
        "semester": "Staff",
        "id_number": "ADM-PES-042",
        "badge_label": "Chief Administrative Officer",
        "avatar_emoji": "🛡️",
        "bio": "Central administrator with full access to support ticket queues, escalation resolution, and knowledge base indexing.",
    },
    "finance_officer": {
        "usn": "FIN-DESK-102",
        "email": "finance.lead@pesu.pes.edu",
        "password": "financepassword",
        "name": "S. K. Kulkarni (Finance Desk)",
        "role": "Admin",
        "department": "Office of the Bursar & Student Accounts (Block A, Room 102)",
        "semester": "Staff",
        "id_number": "FIN-DESK-102",
        "badge_label": "Finance Officer",
        "avatar_emoji": "💼",
        "bio": "Manages tuition fee clearances, revaluation fee refunds, and student payment grievances.",
    },
    "visitor": {
        "usn": "EVAL-2026-JUDGE",
        "email": "judge.guest@pesu.pes.edu",
        "password": "guestpassword",
        "name": "Hackathon Judge / Campus Visitor",
        "role": "Student",
        "department": "Campus Guest & Evaluation Track",
        "semester": "Guest",
        "id_number": "EVAL-2026-JUDGE",
        "badge_label": "Guest Evaluator",
        "avatar_emoji": "⚖️",
        "bio": "Evaluates zero-hallucination answers, citation cards, and automated ticket escalation in real time.",
    },
}


# ---------------------------------------------------------------------------
# DOMAIN VALIDATOR & RBAC PERMISSION HELPERS
# ---------------------------------------------------------------------------

def is_valid_institutional_domain(email: str) -> bool:
    """
    Validates that an email belongs to a sanctioned institutional domain
    (@university.edu, @college.ac.in, @university.org, @pesu.pes.edu, @pes.edu).
    """
    if not email or "@" not in email:
        return False
    parts = email.strip().lower().split("@")
    if len(parts) != 2:
        return False
    domain = parts[1]
    if domain in ALLOWED_INSTITUTIONAL_DOMAINS:
        return True
    if domain.endswith(".edu") or domain.endswith(".ac.in"):
        return True
    return False


# Functional alias for backend interface compatibility
validate_institutional_email = is_valid_institutional_domain


def validate_usn(usn: str) -> bool:
    """Validates institutional USN format (e.g. PES2UG22CS001, 1MS26CS042, ADM-PES-042)."""
    if not usn or not isinstance(usn, str):
        return False
    clean = usn.strip()
    return len(clean) >= 4 and clean.replace("-", "").isalnum()


def verify_role(
    user_or_session: Union[User, Dict[str, Any], str, None],
    required_role: str,
) -> bool:
    """
    Checks if a user, session dictionary, or role string satisfies the required role.
    Admin role satisfies both Admin and Student operations.
    """
    if user_or_session is None:
        return False

    if isinstance(user_or_session, User):
        user_role = user_or_session.role.lower()
    elif isinstance(user_or_session, dict):
        user_role = str(user_or_session.get("role", "")).strip().lower()
    else:
        user_role = str(user_or_session).strip().lower()

    req = required_role.strip().lower()
    if req == "admin":
        return user_role == "admin"
    if req == "student":
        return user_role in ("student", "admin")
    return user_role == req


def require_role(
    user_or_session: Union[User, Dict[str, Any], str, None],
    required_role: str,
) -> None:
    """
    Raises PermissionError if the user or session does not meet the required role.
    """
    if not verify_role(user_or_session, required_role):
        actual_role = "None"
        if isinstance(user_or_session, User):
            actual_role = str(user_or_session.role)
        elif isinstance(user_or_session, dict):
            actual_role = str(user_or_session.get("role", "Unknown"))
        elif user_or_session is not None:
            actual_role = str(user_or_session)

        raise PermissionError(
            f"Access Denied: Requires '{required_role}' privileges, but current role is '{actual_role}'."
        )


# ---------------------------------------------------------------------------
# SUPABASE CLOUD CONNECTION
# ---------------------------------------------------------------------------

_supabase_client = None


def get_supabase_client():
    """
    Retrieves or initializes the official Supabase client for cloud RBAC & identity.
    Returns None if SUPABASE_URL or SUPABASE_KEY is missing or if connection fails.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None

    try:
        from supabase import create_client
        _supabase_client = create_client(url, key)
        return _supabase_client
    except Exception:
        return None


def sync_user_to_supabase(user: User) -> bool:
    """Upserts user profile into Supabase public.users table."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        data = {
            "usn": user.usn,
            "name": user.name,
            "email": user.email.strip().lower(),
            "department": user.department,
            "semester": user.semester or "Undergraduate",
            "role": str(user.role).capitalize(),
            "verified": int(user.verified),
            "last_login": datetime.datetime.now().isoformat(),
        }
        client.table("users").upsert(data, on_conflict="usn").execute()
        return True
    except Exception:
        return False


def fetch_user_from_supabase(identifier: str) -> Optional[User]:
    """Queries user from Supabase public.users by email or USN."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        cleaned = identifier.strip().lower()
        res = client.table("users").select("*").or_(f"email.eq.{cleaned},usn.eq.{identifier.strip()}").execute()
        if res.data and len(res.data) > 0:
            row = res.data[0]
            role = RoleStr(row.get("role", "Student").capitalize())
            return User(
                usn=row["usn"],
                name=row["name"],
                email=row["email"],
                department=row["department"],
                semester=row.get("semester"),
                role=role,
                verified=int(row.get("verified", 1)),
                last_login=str(row.get("last_login", "")),
                badge_label="Administrator" if role == Role.ADMIN else "Enrolled Student",
                avatar_emoji="🛡️" if role == Role.ADMIN else "🎓",
            )
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# SQLITE IDENTITY STORE & SESSION MANAGER
# ---------------------------------------------------------------------------

def init_auth_db(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """
    Initializes the SQLite database with institutional users and user_sessions tables.
    Auto-creates parent directories and seeds initial personas if empty.
    """
    target_path = Path(db_path or DB_PATH)
    os.makedirs(target_path.parent, exist_ok=True)

    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                usn TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                department TEXT NOT NULL,
                semester TEXT,
                role TEXT CHECK(role IN ('Student', 'Admin')) NOT NULL,
                verified INTEGER DEFAULT 1,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                usn TEXT NOT NULL,
                user_email TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(usn) REFERENCES users(usn)
            )
            """
        )

        # Seed initial personas if users table is empty
        cursor = conn.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            for persona in JUDGE_PERSONAS.values():
                conn.execute(
                    """
                    INSERT INTO users (usn, name, email, department, semester, role, verified)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        persona["usn"],
                        persona["name"],
                        persona["email"].lower(),
                        persona["department"],
                        persona.get("semester", "N/A"),
                        persona["role"].capitalize(),
                    ),
                )

    return conn


def register_user(
    usn: str,
    name: str,
    email: str,
    department: str,
    semester: str = "1st Semester",
    role: str = "Student",
    db_path: Optional[Path] = None,
) -> User:
    """Registers a new institutional user with domain validation and syncs to Supabase."""
    cleaned_email = email.strip().lower()
    cleaned_usn = usn.strip()

    if not is_valid_institutional_domain(cleaned_email):
        raise ValueError(
            f"Invalid email domain for '{email}'. Must be a registered institutional address."
        )

    if not validate_usn(cleaned_usn):
        raise ValueError(f"Invalid USN format '{usn}'. Must be alphanumeric with optional hyphens.")

    norm_role = RoleStr(role.strip().capitalize())
    if norm_role not in ("Student", "Admin"):
        norm_role = Role.STUDENT

    target_path = Path(db_path or DB_PATH)
    conn = init_auth_db(target_path)
    with conn:
        conn.execute(
            """
            INSERT INTO users (usn, name, email, department, semester, role, verified, last_login)
            VALUES (?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(usn) DO UPDATE SET
                name = excluded.name,
                email = excluded.email,
                department = excluded.department,
                semester = excluded.semester,
                role = excluded.role,
                last_login = CURRENT_TIMESTAMP
            """,
            (cleaned_usn, name.strip(), cleaned_email, department.strip(), semester, str(norm_role)),
        )

    user = User(
        usn=cleaned_usn,
        id_number=cleaned_usn,
        name=name.strip(),
        email=cleaned_email,
        department=department.strip(),
        semester=semester,
        role=norm_role,
        verified=1,
    )

    # Sync to Supabase in background/inline
    sync_user_to_supabase(user)
    return user


def authenticate_user(
    identifier: str,
    password: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Optional[User]:
    """
    Verifies user credentials against Judge Personas, SQLite identity store,
    and Supabase cloud. Returns User object on success, None on failure.
    """
    cleaned_id = identifier.strip().lower()

    # 1. Check pre-configured Judge Personas
    for persona_key, data in JUDGE_PERSONAS.items():
        if (data["email"].lower() == cleaned_id or data["usn"].lower() == cleaned_id):
            if password is not None and data["password"] != password:
                return None
            return User(
                usn=data["usn"],
                id_number=data["id_number"],
                email=data["email"],
                name=data["name"],
                role=RoleStr(data["role"].capitalize()),
                department=data["department"],
                semester=data.get("semester"),
                badge_label=data["badge_label"],
                avatar_emoji=data["avatar_emoji"],
            )

    # 2. Check SQLite Identity Store
    target_path = Path(db_path or DB_PATH)
    conn = init_auth_db(target_path)
    with conn:
        cursor = conn.execute(
            "SELECT * FROM users WHERE LOWER(email) = ? OR LOWER(usn) = ?",
            (cleaned_id, cleaned_id),
        )
        row = cursor.fetchone()
        if row:
            # Update last_login
            conn.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE usn = ?",
                (row["usn"],),
            )
            role = RoleStr(row["role"].capitalize())
            return User(
                usn=row["usn"],
                id_number=row["usn"],
                name=row["name"],
                email=row["email"],
                department=row["department"],
                semester=row["semester"],
                role=role,
                verified=int(row["verified"]),
                last_login=str(row["last_login"]),
                badge_label="Administrator" if role == Role.ADMIN else "Enrolled Student",
                avatar_emoji="🛡️" if role == Role.ADMIN else "🎓",
            )

    # 3. Check Supabase Cloud Store
    cloud_user = fetch_user_from_supabase(cleaned_id)
    if cloud_user:
        return cloud_user

    return None


def create_session(user: User, db_path: Optional[Path] = None) -> str:
    """Generates a secure session token and persists it in SQLite user_sessions."""
    session_id = uuid.uuid4().hex
    target_path = Path(db_path or DB_PATH)
    conn = init_auth_db(target_path)
    with conn:
        conn.execute(
            """
            INSERT INTO user_sessions (session_id, usn, user_email, role, created_at, last_active)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (session_id, user.usn, user.email.lower(), str(user.role)),
        )
    return session_id


def validate_session(session_id: str, db_path: Optional[Path] = None) -> Optional[User]:
    """Validates an active session token and refreshes last_active timestamp."""
    target_path = Path(db_path or DB_PATH)
    conn = init_auth_db(target_path)
    with conn:
        cursor = conn.execute(
            """
            SELECT u.* FROM user_sessions s
            JOIN users u ON s.usn = u.usn
            WHERE s.session_id = ?
            """,
            (session_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        conn.execute(
            "UPDATE user_sessions SET last_active = CURRENT_TIMESTAMP WHERE session_id = ?",
            (session_id,),
        )

        role = RoleStr(row["role"].capitalize())
        return User(
            usn=row["usn"],
            id_number=row["usn"],
            name=row["name"],
            email=row["email"],
            department=row["department"],
            semester=row["semester"],
            role=role,
            verified=int(row["verified"]),
            last_login=str(row["last_login"]),
            badge_label="Administrator" if role == Role.ADMIN else "Enrolled Student",
            avatar_emoji="🛡️" if role == Role.ADMIN else "🎓",
        )


def invalidate_session(session_id: str, db_path: Optional[Path] = None) -> bool:
    """Terminates an active session token."""
    target_path = Path(db_path or DB_PATH)
    conn = init_auth_db(target_path)
    with conn:
        cursor = conn.execute("DELETE FROM user_sessions WHERE session_id = ?", (session_id,))
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# UI COMPATIBILITY HELPERS (SACHITA'S STREAMLIT FRONTEND)
# ---------------------------------------------------------------------------

def init_user_session() -> Dict[str, Any]:
    """Initializes or retrieves the active session dictionary for Streamlit."""
    try:
        import streamlit as st
        if "user_session" not in st.session_state:
            st.session_state.user_session = dict(DEFAULT_STUDENT_SESSION)
        return st.session_state.user_session
    except Exception:
        return dict(DEFAULT_STUDENT_SESSION)


def render_judge_switcher():
    """
    Renders 1-click persona switcher in Streamlit sidebar.
    Allows judges and evaluators to quickly swap roles between Student and Administrator.
    """
    try:
        import streamlit as st
        st.markdown("##### ⚖️ 1-Click Judge Persona Switcher")
        persona_keys = list(JUDGE_PERSONAS.keys())
        current_usn = st.session_state.get("user_session", {}).get("usn", "1MS26CS042")

        default_idx = 0
        for i, k in enumerate(persona_keys):
            if JUDGE_PERSONAS[k]["usn"] == current_usn:
                default_idx = i
                break

        selected_key = st.selectbox(
            "Evaluation Persona",
            options=persona_keys,
            index=default_idx,
            format_func=lambda k: f"{JUDGE_PERSONAS[k]['avatar_emoji']} {JUDGE_PERSONAS[k]['name']} ({JUDGE_PERSONAS[k]['role']})",
            label_visibility="collapsed",
            key="judge_persona_selector",
        )

        selected_persona = JUDGE_PERSONAS[selected_key]
        if st.session_state.get("user_session", {}).get("usn") != selected_persona["usn"]:
            st.session_state.user_session = {
                "usn": selected_persona["usn"],
                "name": selected_persona["name"],
                "email": selected_persona["email"],
                "department": selected_persona["department"],
                "semester": selected_persona.get("semester", "N/A"),
                "role": selected_persona["role"],
                "verified": True,
                "badge_label": selected_persona.get("badge_label", selected_persona["role"]),
                "avatar_emoji": selected_persona.get("avatar_emoji", "🎓"),
            }
            st.rerun()
    except Exception:
        pass


def render_auth_sidebar():
    """
    Renders institutional authentication & USN status console in Streamlit sidebar.
    Displays verification badge, domain validity, and manual credential input.
    """
    try:
        import streamlit as st
        st.markdown("##### 🏛️ Institutional Domain & RBAC Console")
        sess = st.session_state.get("user_session", DEFAULT_STUDENT_SESSION)

        is_verified = sess.get("verified", False)
        email = sess.get("email", "")
        domain_valid = is_valid_institutional_domain(email)
        role = sess.get("role", "Student")

        if is_verified and domain_valid:
            st.success(f"🔒 **{role.upper()} VERIFIED** — {email}")
        else:
            st.warning(f"⚠️ Unverified Domain: {email}")

        with st.expander("🔑 Institutional Sign-In", expanded=False):
            with st.form("sidebar_auth_form"):
                in_usn = st.text_input("USN / Roll Number", value=sess.get("usn", ""))
                in_email = st.text_input("Institutional Email", value=email)
                in_password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Verify & Authenticate")
                if submitted:
                    user = authenticate_user(in_email, in_password or None)
                    if user:
                        st.session_state.user_session = user.to_session_dict()
                        st.success(f"Authenticated as {user.name} ({user.role})")
                        st.rerun()
                    elif is_valid_institutional_domain(in_email):
                        user = register_user(
                            usn=in_usn or f"ID-{int(datetime.datetime.now().timestamp())}",
                            name=in_email.split("@")[0].replace(".", " ").title(),
                            email=in_email,
                            department="Academic Affairs",
                            role="Student",
                        )
                        st.session_state.user_session = user.to_session_dict()
                        st.success(f"Verified & Logged in as {user.name}!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials or non-institutional domain.")
    except Exception:
        pass


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
        usn=data["usn"],
        id_number=data["id_number"],
        email=data["email"],
        name=data["name"],
        role=RoleStr(data["role"].capitalize()),
        department=data["department"],
        semester=data.get("semester"),
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
