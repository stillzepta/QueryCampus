"""
Session State & Conversational Memory Module.
Complies with IEEE GITCON 2025 Paper Sec. III & Hackathon Plan Task 2.3:
- Rolling 3-message context window to maintain coherence across multi-turn queries.
Maintained by: Krishna Verma (LLM & Backend Integrator)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import time

from querycampus.config import MAX_HISTORY_TURNS


@dataclass
class ChatTurn:
    user_query: str
    assistant_response: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class ConversationMemory:
    """
    Maintains a rolling context window of the last N turns
    (default: 3 turns / 6 message exchanges) for conversational follow-ups.
    """

    def __init__(self, max_turns: int = MAX_HISTORY_TURNS):
        self.max_turns = max_turns
        self.history: List[ChatTurn] = []

    def add_turn(
        self,
        user_query: str,
        assistant_response: str,
        sources: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        turn = ChatTurn(
            user_query=user_query.strip(),
            assistant_response=assistant_response.strip(),
            sources=sources or [],
        )
        self.history.append(turn)
        # Keep only the most recent max_turns
        if len(self.history) > self.max_turns:
            self.history = self.history[-self.max_turns :]

    def get_history_as_context(self) -> str:
        """Serializes rolling turns into formatted dialog history."""
        if not self.history:
            return ""

        dialog_lines = []
        for turn in self.history:
            dialog_lines.append(f"Student: {turn.user_query}")
            dialog_lines.append(f"QueryCampus Receptionist: {turn.assistant_response}")

        return "\n".join(dialog_lines)

    def get_recent_turns(self) -> List[ChatTurn]:
        return list(self.history)

    def clear(self) -> None:
        self.history.clear()
