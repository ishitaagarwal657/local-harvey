"""
Product-specific Ideal Customer Profile (ICP) generation.
"""
from typing import Dict, Any
from ..ollama_client import llm

SYSTEM = """You are an expert in B2B Ideal Customer Profile (ICP) definition.
Create sharp, actionable ICPs that sales teams can use for targeting and personalisation.
Be specific about firmographics, technographics, buying triggers and disqualifiers."""

async def generate_icp(product: Dict[str, Any], business_profile: Dict[str, Any]) -> Dict[str, Any]:
    prompt = f"""Generate a detailed Ideal Customer Profile (ICP) for this product.

Product Name: {product.get('name')}
Product Description: {product.get('description')}
Value Props: {product.get('value_props')}
Pricing Model: {product.get('pricing_model')}

Business Context:
{business_profile}

Return JSON with:
- icp_name
- firmographics: {{industry, company_size, revenue_range, geography, business_model}}
- buyer_personas: list of {{title, seniority, responsibilities, goals, pain_points}}
- buying_triggers: list of signals that indicate readiness
- disqualifiers: list of characteristics that make them a bad fit
- success_criteria: how we know the customer is successful
- messaging_hooks: 3-5 short hooks that resonate with this ICP
"""

    result = await llm.generate_json(prompt, system=SYSTEM, agent="icp")
    return {
        "icp": result["parsed"],
        "model_used": result["model"],
        "latency_ms": result["latency_ms"],
        "prompt_hash": result["prompt_hash"]
    }
