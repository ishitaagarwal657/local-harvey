"""
Personalised outreach email generation.
"""
from typing import Dict, Any, Optional
from ..ollama_client import llm

SYSTEM = """You are an expert cold-email copywriter for B2B sales.
Write short, specific, non-salesy emails that feel researched.
Rules:
- Subject under 50 characters
- Body under 120 words
- No buzzwords, no "I hope this email finds you well"
- One clear soft CTA
- Personalisation must be based on real data provided
"""

async def generate_outreach_email(
    prospect: Dict[str, Any],
    problem: Dict[str, Any],
    product: Dict[str, Any],
    icp: Optional[Dict] = None,
    sequence_step: int = 1
) -> Dict[str, Any]:
    step_guidance = {
        1: "First touch — pure value + observation. No hard ask.",
        2: "Follow-up — add one new insight or social proof.",
        3: "Break-up / last touch — short, respectful, leave the door open."
    }

    prompt = f"""Write a personalised cold email (sequence step {sequence_step}).

Prospect company: {prospect.get('company_name')}
Contact: {prospect.get('contact_name')} — {prospect.get('contact_title')}
Location: {prospect.get('location')}

Problem statement we identified:
{problem}

Our product: {product.get('name')}
Value props: {product.get('value_props')}

Guidance for this step: {step_guidance.get(sequence_step, '')}

Return JSON:
- subject: string
- body: string (plain text, use \\n for line breaks)
- personalisation_points_used: list of specific facts you referenced
- cta_type: "soft_question" | "value_offer" | "meeting" | "resource"
"""

    result = await llm.generate_json(prompt, system=SYSTEM, agent="outreach")
    return {
        "email": result["parsed"],
        "model_used": result["model"],
        "latency_ms": result["latency_ms"],
        "prompt_hash": result["prompt_hash"],
        "sequence_step": sequence_step
    }
