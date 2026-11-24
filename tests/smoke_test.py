"""
Structural smoke test — does not require Ollama.
Run: python -m tests.smoke_test
"""
import sys
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def check_syntax():
    files = list((ROOT / "backend").rglob("*.py"))
    ok = True
    for f in files:
        try:
            ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError as e:
            print(f"SYNTAX FAIL: {f}: {e}")
            ok = False
    return ok

def check_imports():
    # Light import checks that do not need Ollama or torch
    from backend.config import settings, DB_PATH
    from backend.hardware import recommend_model, get_system_info
    assert settings.ollama_host.startswith("http://127.0.0.1")
    assert settings.allow_external_llm is False
    info = get_system_info()
    rec = recommend_model(info)
    assert "recommended" in rec
    print("config + hardware OK")
    print("recommended model:", rec["recommended"])
    return True

def check_sample_data():
    sample = ROOT / "sample_data"
    for name in ("companies.json", "products.json", "prospects.json", "sample_replies.json"):
        p = sample / name
        assert p.exists(), f"missing {p}"
        import json
        data = json.loads(p.read_text())
        assert isinstance(data, list) and len(data) > 0
    print("sample_data OK")
    return True

def main():
    print("=== LocalHarvey smoke test ===")
    assert check_syntax(), "syntax errors"
    print("syntax OK")
    assert check_sample_data()
    assert check_imports()
    print("=== ALL SMOKE CHECKS PASSED ===")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
