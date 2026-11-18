"""
QueryCampus Core Engine Package.
"""

from .auth import authenticate_user, get_demo_user, User
from .ingest import DocumentIngestor, RecursiveTextSplitter, DocumentChunk
from .vector_store import ChromaVectorStore
from .retrieval import CampusRetriever, retrieve_context, CONFIDENCE_THRESHOLD
from .generator import CampusGenerator, ConversationMemory
from .ticketing import TicketingSystem, Ticket
from .backend_interface import (
    process_student_turn,
    create_escalation_ticket,
    get_student_tickets,
    get_admin_tickets,
    update_admin_ticket,
)

__all__ = [
    "authenticate_user",
    "get_demo_user",
    "User",
    "DocumentIngestor",
    "RecursiveTextSplitter",
    "DocumentChunk",
    "ChromaVectorStore",
    "CampusRetriever",
    "retrieve_context",
    "CONFIDENCE_THRESHOLD",
    "CampusGenerator",
    "ConversationMemory",
    "TicketingSystem",
    "Ticket",
    "process_student_turn",
    "create_escalation_ticket",
    "get_student_tickets",
    "get_admin_tickets",
    "update_admin_ticket",
]
