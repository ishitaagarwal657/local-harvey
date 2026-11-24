"""
Local embeddings via Sentence Transformers.
MIT-licensed models only. Fully offline after first download.
Used lightly for prospect similarity / scoring support.
If the model cannot be loaded, callers receive a clear fallback.
"""
from typing import List, Optional, Dict, Any
import hashlib
import json

_model = None
_model_name = None
_load_error: Optional[str] = None


def _lazy_load(model_name: str = "all-MiniLM-L6-v2"):
    global _model, _model_name, _load_error
    if _model is not None and _model_name == model_name:
        return _model
    if _load_error and _model_name == model_name:
        return None
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(model_name)
        _model_name = model_name
        _load_error = None
        return _model
    except Exception as e:
        _load_error = str(e)
        _model = None
        return None


def embed_texts(texts: List[str], model_name: str = "all-MiniLM-L6-v2") -> Dict[str, Any]:
    """
    Return local embeddings or a deterministic hash-based fallback.
    Never calls an external embedding API.
    """
    model = _lazy_load(model_name)
    if model is None:
        # Deterministic local fallback so offline workflows still work
        vectors = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            # 32-dim pseudo-vector from hash (not semantic, but stable)
            vec = [((b / 255.0) * 2 - 1) for b in h[:32]]
            vectors.append(vec)
        return {
            "embeddings": vectors,
            "model": "hash-fallback",
            "note": f"Sentence-Transformers unavailable ({_load_error}). Using deterministic local hash vectors.",
            "dimension": 32
        }

    vectors = model.encode(texts, show_progress_bar=False).tolist()
    return {
        "embeddings": vectors,
        "model": model_name,
        "note": "Local Sentence-Transformers embedding",
        "dimension": len(vectors[0]) if vectors else 0
    }


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
