"""
Reply classification using sample conversations.
Works fully offline.
"""
from typing import Dict, Any
from ..ollama_client import llm

SYSTEM = """You are an expert at classifying sales email replies.
Classify accurately into one of the allowed categories and extract intent.
Be conservative — if unclear, use "other"."""

CATEGORIES = [
    "interested",
    "meeting_request",
    "objection",
    "not_interested",
    "out_of_office",
    "unsubscribe",
    "wrong_person",
    "other"
]

async def classify_reply(reply_text: str, original_email: str = "") -> Dict[str, Any]:
    prompt = f"""Classify this sales reply.

Original outreach (if available):
{original_email[:800] if original_email else "N/A"}

Reply:
\"\"\"
{reply_text}
\"\"\"

Allowed categories: {CATEGORIES}

Return JSON:
- classification: one of the allowed categories
- confidence: 0.0-1.0
- intent_summary: one sentence
- suggested_next_action: string
- key_phrases: list of phrases that drove the classification
"""

    result = await llm.generate_json(prompt, system=SYSTEM, agent="reply_classifier")
    return {
        "classification": result["parsed"],
        "model_used": result["model"],
        "latency_ms": result["latency_ms"],
        "prompt_hash": result["prompt_hash"]
    }
