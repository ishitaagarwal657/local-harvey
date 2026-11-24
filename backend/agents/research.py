"""
Prospect research agent.
Primary path: uses previously downloaded / stored data (fully offline).
Optional path: when internet is available and allow_web=True, may enrich
with public page text via BeautifulSoup. This enrichment is clearly separated
from local LLM inference and is never required for core offline workflows.
"""
from typing import Dict, Any, Optional
from ..ollama_client import llm


SYSTEM = """You are a B2B research analyst.
Given whatever information is available about a prospect company,
produce a structured research summary useful for sales outreach.
Never invent facts that are not supported by the provided data.
If information is missing, clearly mark it as unknown."""


async def research_prospect(
    prospect: Dict[str, Any],
    product_context: Optional[Dict] = None,
    extra_notes: str = "",
    allow_web: bool = False,
) -> Dict[str, Any]:
    web_snippet = ""
    web_meta = {"attempted": False, "ok": False}

    # Optional online enrichment — never required for offline acceptance test
    if allow_web and prospect.get("website"):
        try:
            from ..utils.web_research import fetch_page_text, is_probably_online
            if is_probably_online():
                web_meta["attempted"] = True
                page = await fetch_page_text(prospect["website"])
                web_meta["ok"] = page.get("ok", False)
                if page.get("ok") and page.get("text"):
                    web_snippet = f"\n\nPublic website excerpt (title: {page.get('title', '')}):\n{page['text'][:2500]}"
        except Exception as e:
            web_meta["error"] = str(e)

    context = f"""
Prospect Company: {prospect.get('company_name')}
Website: {prospect.get('website', 'unknown')}
Location: {prospect.get('location', 'unknown')}
Contact: {prospect.get('contact_name')} — {prospect.get('contact_title')}
Existing notes / raw data:
{prospect.get('raw_data', '')}
{prospect.get('research_notes', '')}
{extra_notes}
{web_snippet}
"""
    if product_context:
        context += f"\nProduct we are selling: {product_context.get('name')} — {product_context.get('description')}"

    prompt = f"""Research and summarise this prospect for sales purposes.

{context}

Return JSON:
- company_overview (2-4 sentences based only on available data)
- likely_pain_points (list)
- relevant_signals_observed (list)
- decision_maker_fit (how well the contact matches a typical buyer)
- research_confidence (high / medium / low)
- recommended_next_action
- unknowns (list of important missing information)
- data_sources_used (list: e.g. "stored_raw_data", "website_excerpt")
"""

    result = await llm.generate_json(prompt, system=SYSTEM, agent="research")
    parsed = result["parsed"]
    if "data_sources_used" not in parsed:
        sources = ["stored_raw_data"]
        if web_snippet:
            sources.append("website_excerpt")
        parsed["data_sources_used"] = sources

    return {
        "research": parsed,
        "model_used": result["model"],
        "latency_ms": result["latency_ms"],
        "prompt_hash": result["prompt_hash"],
        "web_enrichment": web_meta,
    }
