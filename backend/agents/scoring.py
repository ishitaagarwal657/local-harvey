"""
Prospect scoring & prioritisation.
Primary path: local LLM.
Fallback path (Ollama unavailable): deterministic rule-based scorer — no cloud.
Also uses local embeddings for ICP-fit similarity when available.
"""
from typing import Dict, Any, Optional
from ..ollama_client import llm, LocalLLMError
from ..embeddings import embed_texts, cosine_similarity

SYSTEM = """You are a sales operations analyst.
Score prospects 0-100 based on ICP fit, buying signals, urgency and data quality.
Be consistent and explain your reasoning. Return only valid JSON."""


def _deterministic_score(
    prospect: Dict[str, Any],
    research: Dict[str, Any],
    signals: Dict[str, Any],
    icp: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Rule-based scorer used when local LLM is unavailable.
    Transparent, no external calls, no hard-coded fake intelligence presented as AI.
    """
    score = 40  # base
    reasons = []

    # Data quality
    raw = (prospect.get("raw_data") or "") + (prospect.get("research_notes") or "")
    if len(raw) > 200:
        score += 12
        reasons.append("rich stored data")
    elif len(raw) > 50:
        score += 6
        reasons.append("some stored data")

    # Contact seniority heuristics
    title = (prospect.get("contact_title") or "").lower()
    if any(k in title for k in ("owner", "founder", "ceo", "vp", "director", "head")):
        score += 12
        reasons.append("senior contact")
    elif any(k in title for k in ("manager", "lead", "principal")):
        score += 7
        reasons.append("manager-level contact")

    # Signal strength from previous classification if present
    overall = ""
    if isinstance(signals, dict):
        overall = str(signals.get("overall_strength") or signals.get("signal_strength") or "").lower()
        if "strong" in overall:
            score += 18
            reasons.append("strong buying signals")
        elif "moderate" in overall:
            score += 10
            reasons.append("moderate signals")
        elif "weak" in overall:
            score += 3

    # Research confidence
    conf = str((research or {}).get("research_confidence") or "").lower()
    if conf == "high":
        score += 10
        reasons.append("high research confidence")
    elif conf == "medium":
        score += 5

    # Embedding similarity to ICP text (if available)
    try:
        icp_text = " ".join([
            str(icp.get("icp_name") or ""),
            str(icp.get("firmographics") or ""),
            " ".join(icp.get("ideal_personas") or []) if isinstance(icp.get("ideal_personas"), list) else str(icp.get("ideal_personas") or ""),
        ])
        prospect_text = " ".join([
            prospect.get("company_name") or "",
            prospect.get("contact_title") or "",
            prospect.get("raw_data") or "",
            str((research or {}).get("company_overview") or ""),
        ])
        if icp_text.strip() and prospect_text.strip():
            emb = embed_texts([icp_text, prospect_text])
            if len(emb["embeddings"]) == 2:
                sim = cosine_similarity(emb["embeddings"][0], emb["embeddings"][1])
                # map -1..1-ish / 0..1 to 0..15
                fit_pts = int(max(0, min(15, sim * 15)))
                score += fit_pts
                reasons.append(f"embedding ICP fit ~{sim:.2f} (+{fit_pts})")
    except Exception:
        pass

    score = max(0, min(100, score))
    priority = "high" if score >= 70 else ("medium" if score >= 45 else "low")

    return {
        "score": score,
        "score_breakdown": {
            "icp_fit": "rule+embedding",
            "signal_strength": overall or "unknown",
            "data_quality": "heuristic",
            "mode": "deterministic_fallback",
        },
        "priority": priority,
        "reason": "Deterministic local scorer (Ollama unavailable). Factors: " + "; ".join(reasons) if reasons else "base score only",
        "recommended_action": "Re-run with local LLM when Ollama is available for full AI scoring",
        "fallback": True,
    }


async def score_prospect(
    prospect: Dict[str, Any],
    research: Dict[str, Any],
    signals: Dict[str, Any],
    icp: Dict[str, Any],
) -> Dict[str, Any]:
    prompt = f"""Score this prospect for prioritisation.

Prospect: {prospect.get('company_name')}
Contact: {prospect.get('contact_name')} ({prospect.get('contact_title')})

Research confidence: {research.get('research_confidence') if isinstance(research, dict) else 'n/a'}
Research overview: {research.get('company_overview') if isinstance(research, dict) else research}

Signals: {signals}

ICP summary: {icp.get('icp_name') if isinstance(icp, dict) else ''} — {icp.get('firmographics') if isinstance(icp, dict) else icp}

Return JSON:
- score: number 0-100
- score_breakdown: {{
    icp_fit: 0-25,
    signal_strength: 0-25,
    data_quality: 0-15,
    urgency: 0-20,
    contact_seniority: 0-15
  }}
- priority: "high" | "medium" | "low"
- reason: 2-3 sentence explanation
- recommended_action: string
"""

    try:
        result = await llm.generate_json(prompt, system=SYSTEM, agent="scoring")
        parsed = result["parsed"]
        # Light validation
        if not isinstance(parsed.get("score"), (int, float)):
            try:
                parsed["score"] = float(parsed.get("score", 0))
            except Exception:
                parsed["score"] = 50
        parsed["score"] = max(0, min(100, float(parsed["score"])))
        parsed["fallback"] = False
        return {
            "scoring": parsed,
            "model_used": result["model"],
            "latency_ms": result["latency_ms"],
            "prompt_hash": result["prompt_hash"],
        }
    except LocalLLMError:
        # Deterministic non-LLM path — required by assignment
        det = _deterministic_score(prospect, research or {}, signals or {}, icp or {})
        return {
            "scoring": det,
            "model_used": "deterministic-rules",
            "latency_ms": 0,
            "prompt_hash": "fallback",
            "note": "Ollama unavailable — used local rule-based scorer (no cloud).",
        }
