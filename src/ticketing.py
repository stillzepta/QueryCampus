"""
Ticketing & Escalation Management System.
Persists support tickets and administrative escalations into SQLite storage.
Supports automated escalation triggers for Lost & Found, grievances, and low-confidence RAG queries.
"""

import os
import sqlite3
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = Path(os.getenv("DB_DIR", BASE_DIR / "data" / "db"))
DB_PATH = Path(os.getenv("DB_PATH", DB_DIR / "campus.db"))


@dataclass
class Ticket:
    id: int
    ticket_number: str
    user_email: str
    user_name: str
    category: str
    title: str
    description: str
    status: str
    priority: str
    created_at: str
    admin_notes: Optional[str] = None


class TicketingSystem:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        os.makedirs(self.db_path.parent, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_number TEXT UNIQUE NOT NULL,
                    user_email TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Open',
                    priority TEXT NOT NULL DEFAULT 'Medium',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    admin_notes TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_email TEXT NOT NULL,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def create_ticket(
        self,
        user_email: str,
        user_name: str,
        category: str,
        title: str,
        description: str,
        priority: str = "Medium",
    ) -> Ticket:
        now_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Generate ticket number
            cursor.execute("SELECT COUNT(*) FROM tickets")
            count = cursor.fetchone()[0] + 1
            ticket_number = f"QC-{now_str[:8]}-{count:04d}"

            cursor.execute(
                """
                INSERT INTO tickets (ticket_number, user_email, user_name, category, title, description, priority, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Open')
                """,
                (ticket_number, user_email, user_name, category, title, description, priority),
            )
            ticket_id = cursor.lastrowid
            conn.commit()

            return Ticket(
                id=ticket_id,
                ticket_number=ticket_number,
                user_email=user_email,
                user_name=user_name,
                category=category,
                title=title,
                description=description,
                status="Open",
                priority=priority,
                created_at=datetime.datetime.now().isoformat(),
                admin_notes=None,
            )

    def get_all_tickets(self, status_filter: Optional[str] = None) -> List[Ticket]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status_filter and status_filter != "All":
                cursor.execute(
                    "SELECT * FROM tickets WHERE status = ? ORDER BY id DESC",
                    (status_filter,),
                )
            else:
                cursor.execute("SELECT * FROM tickets ORDER BY id DESC")

            rows = cursor.fetchall()
            return [
                Ticket(
                    id=row["id"],
                    ticket_number=row["ticket_number"],
                    user_email=row["user_email"],
                    user_name=row["user_name"],
                    category=row["category"],
                    title=row["title"],
                    description=row["description"],
                    status=row["status"],
                    priority=row["priority"],
                    created_at=str(row["created_at"]),
                    admin_notes=row["admin_notes"],
                )
                for row in rows
            ]

    def get_user_tickets(self, user_email: str) -> List[Ticket]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM tickets WHERE user_email = ? ORDER BY id DESC",
                (user_email.strip().lower(),),
            )
            rows = cursor.fetchall()
            return [
                Ticket(
                    id=row["id"],
                    ticket_number=row["ticket_number"],
                    user_email=row["user_email"],
                    user_name=row["user_name"],
                    category=row["category"],
                    title=row["title"],
                    description=row["description"],
                    status=row["status"],
                    priority=row["priority"],
                    created_at=str(row["created_at"]),
                    admin_notes=row["admin_notes"],
                )
                for row in rows
            ]

    def update_ticket_status(self, ticket_id: int, new_status: str, admin_notes: Optional[str] = None) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if admin_notes is not None:
                cursor.execute(
                    "UPDATE tickets SET status = ?, admin_notes = ? WHERE id = ?",
                    (new_status, admin_notes, ticket_id),
                )
            else:
                cursor.execute(
                    "UPDATE tickets SET status = ? WHERE id = ?",
                    (new_status, ticket_id),
                )
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def detect_escalation_intent(query: str) -> Optional[str]:
        """
        Determines whether user inquiry indicates a need for human escalation
        (e.g., lost & found, facilities breakdown, fee disputes).
        """
        q = query.lower()
        if any(w in q for w in ["lost", "found", "missing wallet", "missing id", "misplaced", "lost card"]):
            return "Lost & Found"
        if any(w in q for w in ["broken", "repair", "not working", "water leak", "ac not working", "fan not working"]):
            return "Hostel Maintenance"
        if any(w in q for w in ["complaint", "harassment", "dispute", "ragging", "disciplinary"]):
            return "Academic Escalation"
        if any(w in q for w in ["fee refund", "overcharged", "scholarship delay", "payment failure"]):
            return "Fee Grievance"
        return None
