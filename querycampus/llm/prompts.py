"""
Strict Context-Injection Prompt Engine.
Complies with IEEE GITCON 2025 Paper Sec. IV-B & Hackathon Plan Task 2.2:
- Strict prompt format: "Answer based only on: {context} Question: {query} Answer:"
- Zero-hallucination guardrails and source grounding.
Maintained by: Krishna Verma (LLM & Backend Integrator)
"""

from typing import List, Dict, Any, Optional


SYSTEM_GUARDRAIL_INSTRUCTION = (
    "You are QueryCampus, the official AI Virtual Receptionist and Campus Concierge "
    "for PES University. Your primary mandate is strict factual accuracy.\n"
    "Rules:\n"
    "1. Answer based ONLY on the provided retrieved context.\n"
    "2. If the answer cannot be directly determined from the context, respond: "
    "'The official university documentation does not specify this information. "
    "Please contact the relevant department office.'\n"
    "3. Do not invent office room numbers, fees, percentages, or academic dates.\n"
    "4. Keep responses concise, helpful, professional, and clear."
)


class StrictPromptEngine:
    def __init__(self, system_instruction: str = SYSTEM_GUARDRAIL_INSTRUCTION):
        self.system_instruction = system_instruction

    def format_context(self, hits: List[Dict[str, Any]]) -> str:
        """Formats retrieved chunks with citations for LLM injection."""
        if not hits:
            return "No official university records retrieved."

        formatted_parts = []
        for i, hit in enumerate(hits, start=1):
            source = hit.get("metadata", {}).get("source", "Official Document")
            page = hit.get("metadata", {}).get("page", 1)
            text = hit.get("text", "").strip()
            formatted_parts.append(
                f"[Source {i}: {source} (Page {page})]\n{text}"
            )

        return "\n\n".join(formatted_parts)

    def build_prompt(
        self,
        query: str,
        retrieved_hits: List[Dict[str, Any]],
        chat_history_str: Optional[str] = None,
    ) -> str:
        """
        Constructs the strict prompt template matching the IEEE conference paper:
        Answer based only on: {context} Question: {query} Answer:
        """
        context = self.format_context(retrieved_hits)

        history_section = ""
        if chat_history_str:
            history_section = f"Previous Conversation Context:\n{chat_history_str}\n\n"

        prompt = (
            f"{self.system_instruction}\n\n"
            f"{history_section}"
            f"Answer based only on:\n{context}\n\n"
            f"Question: {query}\n"
            f"Answer:"
        )
        return prompt
