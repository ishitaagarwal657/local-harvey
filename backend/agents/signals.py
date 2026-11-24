"""
Buying-signal classification agent.
"""
from typing import Dict, Any, List
from ..ollama_client import llm

SYSTEM = """You are an expert at detecting buying signals for B2B software and services.
Classify observed signals as strong / moderate / weak and explain why.
Only use evidence present in the input."""

async def classify_buying_signals(
    prospect: Dict[str, Any],
    research: Dict[str, Any],
    icp: Dict[str, Any]
) -> Dict[str, Any]:
    prompt = f"""Classify buying signals for this prospect.

Prospect: {prospect.get('company_name')}
Contact: {prospect.get('contact_name')} ({prospect.get('contact_title')})

Research summary:
{research}

ICP buying triggers:
{icp.get('buying_triggers', [])}

Return JSON:
- signals: list of {{
    signal: string,
    strength: "strong" | "moderate" | "weak",
    evidence: string,
    relevance_to_icp: string
  }}
- overall_signal_strength: "strong" | "moderate" | "weak" | "none"
- summary: 1-2 sentence explanation
"""

    result = await llm.generate_json(prompt, system=SYSTEM, agent="signals")
    return {
        "signals": result["parsed"],
        "model_used": result["model"],
        "latency_ms": result["latency_ms"],
        "prompt_hash": result["prompt_hash"]
    }
