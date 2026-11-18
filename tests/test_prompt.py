import pytest
from querycampus.llm.prompts import StrictPromptEngine

def test_strict_prompt_engine_formatting():
    engine = StrictPromptEngine()
    hits = [
        {
            "text": "The minimum attendance required is 75%.",
            "metadata": {"source": "academic_regulations.pdf", "page": 1},
        }
    ]

    prompt = engine.build_prompt("What is the attendance rule?", hits)
    assert "academic_regulations.pdf" in prompt
    assert "Page 1" in prompt
    assert "Answer based only on:" in prompt
    assert "Question: What is the attendance rule?" in prompt
    assert "Answer:" in prompt

def test_empty_hits_formatting():
    engine = StrictPromptEngine()
    prompt = engine.build_prompt("Where is the lab?", [])
    assert "No official university records retrieved." in prompt
