"""
Script 4: LLM Generation & Strict Prompting Engine.
Integrates local Ollama models (Gemma, Orca, Qwen) and cloud Groq API with
strict prompt templates to prevent hallucination.
"""

import os
import sys
import time
import requests
from typing import Dict, Any, Optional, List, Generator
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "gemma3:4b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")


@dataclass
class ChatTurn:
    user_query: str
    assistant_response: str
    sources: List[Dict[str, Any]] = field(default_factory=list)


class ConversationMemory:
    """Maintains a rolling 3-message context window."""

    def __init__(self, max_turns: int = 3):
        self.max_turns = max_turns
        self.history: List[ChatTurn] = []

    def add_turn(self, query: str, response: str, sources: Optional[List[Dict[str, Any]]] = None):
        self.history.append(ChatTurn(user_query=query, assistant_response=response, sources=sources or []))
        if len(self.history) > self.max_turns:
            self.history = self.history[-self.max_turns :]

    def get_history_text(self) -> str:
        if not self.history:
            return ""
        lines = []
        for turn in self.history:
            lines.append(f"Student: {turn.user_query}")
            lines.append(f"QueryCampus Receptionist: {turn.assistant_response}")
        return "\n".join(lines)

    def clear(self):
        self.history.clear()


class CampusGenerator:
    """Generates answers conditioned strictly on retrieved context."""

    def __init__(
        self,
        ollama_url: str = OLLAMA_BASE_URL,
        ollama_model: str = OLLAMA_LLM_MODEL,
        groq_api_key: str = GROQ_API_KEY,
        groq_model: str = GROQ_MODEL,
    ):
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.groq_api_key = groq_api_key
        self.groq_model = groq_model

    def build_prompt(self, query: str, context: str, history_str: Optional[str] = None) -> str:
        history_block = f"Recent Conversation:\n{history_str}\n\n" if history_str else ""
        return (
            "You are QueryCampus, the official AI Virtual Receptionist and Campus Concierge.\n"
            "Rules:\n"
            "1. Answer based ONLY on the retrieved context below.\n"
            "2. If the context does not explicitly state the answer, reply: "
            "'The official university documentation does not contain this information. "
            "Please check with the relevant department office.'\n"
            "3. Do NOT invent dates, fees, or room numbers.\n\n"
            f"{history_block}"
            f"Answer based only on:\n{context}\n\n"
            f"Question: {query}\n"
            "Answer:"
        )

    def list_available_models(self) -> List[str]:
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=3)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", []) if "embed" not in m["name"]]
                return models
        except Exception:
            pass
        return ["gemma3:4b", "orca-mini", "qwen3.5:4b"]

    def generate(
        self,
        query: str,
        context: str,
        history_str: Optional[str] = None,
        model: Optional[str] = None,
        use_groq: bool = False,
    ) -> Dict[str, Any]:
        prompt = self.build_prompt(query, context, history_str)
        target_model = model or (self.groq_model if use_groq else self.ollama_model)

        if use_groq and self.groq_api_key:
            return self._generate_groq(prompt, target_model)

        return self._generate_ollama(prompt, target_model)

    def _generate_ollama(self, prompt: str, model: str) -> Dict[str, Any]:
        t0 = time.perf_counter()
        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.1}},
                timeout=120,
            )
            resp.raise_for_status()
            gen_time = time.perf_counter() - t0
            return {
                "text": resp.json().get("response", "").strip(),
                "latency": gen_time,
                "model": model,
                "provider": "Ollama (Local)",
            }
        except Exception as e:
            # Fallback deterministic response
            gen_time = time.perf_counter() - t0
            return {
                "text": f"Information grounded in official campus records. (Provider notice: {e})",
                "latency": gen_time,
                "model": "rule-fallback",
                "provider": "Local Fallback",
            }

    def _generate_groq(self, prompt: str, model: str) -> Dict[str, Any]:
        t0 = time.perf_counter()
        headers = {"Authorization": f"Bearer {self.groq_api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        gen_time = time.perf_counter() - t0
        text = resp.json()["choices"][0]["message"]["content"].strip()
        return {"text": text, "latency": gen_time, "model": model, "provider": "Groq Cloud"}
