import pytest
from querycampus.llm.memory import ConversationMemory

def test_conversation_memory_rolling_window():
    mem = ConversationMemory(max_turns=3)

    mem.add_turn("Q1", "A1")
    mem.add_turn("Q2", "A2")
    mem.add_turn("Q3", "A3")
    assert len(mem.get_recent_turns()) == 3

    # Add 4th turn, 1st should roll off
    mem.add_turn("Q4", "A4")
    turns = mem.get_recent_turns()
    assert len(turns) == 3
    assert turns[0].user_query == "Q2"
    assert turns[-1].user_query == "Q4"

    context_str = mem.get_history_as_context()
    assert "Student: Q2" in context_str
    assert "Student: Q4" in context_str
    assert "Student: Q1" not in context_str

def test_clear_memory():
    mem = ConversationMemory(max_turns=3)
    mem.add_turn("Q1", "A1")
    mem.clear()
    assert len(mem.get_recent_turns()) == 0
    assert mem.get_history_as_context() == ""
