"""
Business Profile Generation Agent
Works fully offline from stored company + product information.
"""
from typing import Dict, Any
from ..ollama_client import llm

SYSTEM = """You are an expert B2B sales strategist and product marketer.
Given company and product information, produce a clear, structured business profile
that a sales agent can use for ICP generation and outreach.
Be specific, practical and concise. Use only the information provided."""

async def generate_business_profile(company: Dict[str, Any], products: list) -> Dict[str, Any]:
    product_text = ""
    for p in products:
        product_text += f"""
Product: {p.get('name')}
Description: {p.get('description')}
Value props: {p.get('value_props')}
Pricing: {p.get('pricing_model')}
"""

    prompt = f"""Create a professional business profile for the following company.

Company Name: {company.get('name')}
Website: {company.get('website', 'N/A')}
Industry: {company.get('industry', 'N/A')}
Description: {company.get('description', 'N/A')}

Products:
{product_text}

Return a JSON object with these keys:
- company_summary (2-3 sentences)
- core_value_proposition
- ideal_customer_characteristics (list of 4-6 bullets)
- key_differentiators (list)
- common_pain_points_addressed (list)
- sales_motion (one of: outbound, inbound, product-led, partnership, mixed)
- suggested_outreach_angle
"""

    result = await llm.generate_json(prompt, system=SYSTEM, agent="business_profile")
    return {
        "profile": result["parsed"],
        "model_used": result["model"],
        "latency_ms": result["latency_ms"],
        "prompt_hash": result["prompt_hash"]
    }
