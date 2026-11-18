import pytest
from src.generator import CampusGenerator, ConversationMemory

def test_prompt_building():
    gen = CampusGenerator()
    prompt = gen.build_prompt(
        query="What is the rule?",
        context="Rule: 75% attendance.",
        history_str="Student: Hi\nQueryCampus Receptionist: Hello",
    )
    assert "Rule: 75% attendance." in prompt
    assert "Question: What is the rule?" in prompt
    assert "Recent Conversation:" in prompt

def test_conversation_memory():
    mem = ConversationMemory(max_turns=3)
    mem.add_turn("Q1", "A1")
    mem.add_turn("Q2", "A2")
    mem.add_turn("Q3", "A3")
    assert len(mem.history) == 3

    mem.add_turn("Q4", "A4")
    assert len(mem.history) == 3
    assert mem.history[0].user_query == "Q2"
    assert mem.history[-1].user_query == "Q4"

    text = mem.get_history_text()
    assert "Student: Q2" in text
    assert "Student: Q4" in text
