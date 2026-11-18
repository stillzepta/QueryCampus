"""
QueryCampus Core Engine Package.
"""

from .auth import authenticate_user, get_demo_user, User
from .ingest import DocumentIngestor, RecursiveTextSplitter, DocumentChunk
from .vector_store import ChromaVectorStore
from .retrieval import CampusRetriever
from .generator import CampusGenerator, ConversationMemory
from .ticketing import TicketingSystem, Ticket

__all__ = [
    "authenticate_user",
    "get_demo_user",
    "User",
    "DocumentIngestor",
    "RecursiveTextSplitter",
    "DocumentChunk",
    "ChromaVectorStore",
    "CampusRetriever",
    "CampusGenerator",
    "ConversationMemory",
    "TicketingSystem",
    "Ticket",
]
