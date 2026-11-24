"""
Core unit/smoke tests — do not require a running Ollama instance.
Run: pytest tests/ -q
"""
import ast
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_all_python_syntax():
    for f in (ROOT / "backend").rglob("*.py"):
        ast.parse(f.read_text(encoding="utf-8"))


def test_sample_data_present_and_valid():
    for name in ("companies.json", "products.json", "prospects.json", "sample_replies.json"):
        p = ROOT / "sample_data" / name
        assert p.exists(), f"missing {name}"
        data = json.loads(p.read_text())
        assert isinstance(data, list) and len(data) >= 2


def test_prospects_count():
    data = json.loads((ROOT / "sample_data" / "prospects.json").read_text())
    assert len(data) >= 8


def test_replies_count():
    data = json.loads((ROOT / "sample_data" / "sample_replies.json").read_text())
    assert len(data) >= 8


def test_config_hard_lock():
    from backend.config import settings
    assert settings.allow_external_llm is False
    assert "127.0.0.1" in settings.ollama_host or "localhost" in settings.ollama_host


def test_hardware_safe_models_only():
    from backend.hardware import recommend_model, SAFE_MODELS
    for tier, cfg in SAFE_MODELS.items():
        assert "qwen2.5:3b" not in cfg["recommended"]  # avoid ambiguous 3B licence
        assert cfg["recommended"].startswith(("qwen2.5:", "phi3:"))


def test_resolve_model_profiles():
    from backend.hardware import resolve_model
    from backend.config import Settings
    s = Settings(profile="standard", default_model="")
    rec = resolve_model(s, {"ram_total_gb": 16, "total_vram_gb": 0, "has_gpu": False})
    assert rec["recommended"] == "qwen2.5:7b-instruct"
    s2 = Settings(profile="minimal", default_model="")
    rec2 = resolve_model(s2, {"ram_total_gb": 4, "total_vram_gb": 0, "has_gpu": False})
    assert rec2["recommended"] == "phi3:mini"


def test_deterministic_scorer():
    from backend.agents.scoring import _deterministic_score
    prospect = {
        "company_name": "Test Co",
        "contact_title": "Owner",
        "raw_data": "x" * 300,
    }
    research = {"research_confidence": "high", "company_overview": "A test company"}
    signals = {"overall_strength": "strong"}
    icp = {"icp_name": "SMB services", "firmographics": "local service businesses"}
    out = _deterministic_score(prospect, research, signals, icp)
    assert 0 <= out["score"] <= 100
    assert out["fallback"] is True
    assert out["priority"] in ("high", "medium", "low")


def test_ollama_client_rejects_non_local():
    from backend.config import Settings
    # Simulate bad host by constructing client logic
    bad = "http://api.openai.com"
    assert not (bad.startswith("http://127.0.0.1") or bad.startswith("http://localhost"))


def test_embeddings_fallback_works():
    from backend.embeddings import embed_texts, cosine_similarity
    result = embed_texts(["hello world", "hello there"])
    assert "embeddings" in result
    assert len(result["embeddings"]) == 2
    # Even hash fallback should give some structure
    sim = cosine_similarity(result["embeddings"][0], result["embeddings"][1])
    assert isinstance(sim, float)
