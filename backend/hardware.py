"""
Hardware detection and model recommendation.
Only recommends models with permissive licences (Apache-2.0 / MIT).
"""
from typing import Dict, Any, Optional
import os

try:
    import psutil
except ImportError:
    psutil = None

try:
    import GPUtil
except ImportError:
    GPUtil = None


# Safe models only (Apache-2.0 or MIT). Avoid Qwen Research License variants.
SAFE_MODELS = {
    "minimal": {
        "recommended": "phi3:mini",           # MIT
        "fallback": "qwen2.5:1.5b-instruct", # Apache-2.0 (smallest Qwen2.5)
        "reason": "Low RAM — smallest capable permissive models",
    },
    "standard": {
        "recommended": "qwen2.5:7b-instruct",  # Apache-2.0
        "fallback": "phi3:mini",              # MIT
        "reason": "Ordinary laptop (8–16 GB RAM) — 7B quality/speed balance",
    },
    "high": {
        "recommended": "qwen2.5:14b-instruct", # Apache-2.0
        "fallback": "qwen2.5:7b-instruct",
        "reason": "High RAM / GPU — 14B for better quality",
    },
    "max": {
        "recommended": "qwen2.5:32b-instruct", # Apache-2.0
        "fallback": "qwen2.5:14b-instruct",
        "reason": "High VRAM GPU or 32GB+ RAM — maximum quality",
    },
}


def get_system_info() -> Dict[str, Any]:
    ram_total_gb = 8.0
    ram_available_gb = 4.0
    cpu_logical = os.cpu_count() or 4
    cpu_physical = cpu_logical // 2
    gpus = []
    total_vram_gb = 0.0

    if psutil:
        mem = psutil.virtual_memory()
        ram_total_gb = round(mem.total / (1024 ** 3), 1)
        ram_available_gb = round(mem.available / (1024 ** 3), 1)
        cpu_logical = psutil.cpu_count(logical=True) or cpu_logical
        cpu_physical = psutil.cpu_count(logical=False) or cpu_physical

    if GPUtil:
        try:
            for g in GPUtil.getGPUs():
                gpus.append({
                    "name": g.name,
                    "memory_total_mb": g.memoryTotal,
                    "memory_used_mb": g.memoryUsed,
                })
                total_vram_gb += g.memoryTotal / 1024
        except Exception:
            pass

    return {
        "ram_total_gb": ram_total_gb,
        "ram_available_gb": ram_available_gb,
        "cpu_logical": cpu_logical,
        "cpu_physical": cpu_physical,
        "gpus": gpus,
        "total_vram_gb": round(total_vram_gb, 1),
        "has_gpu": len(gpus) > 0,
    }


def recommend_model(info: Optional[Dict] = None, profile: Optional[str] = None) -> Dict[str, Any]:
    """
    Recommend a permissive-licence Ollama model based on resources or explicit profile.
    """
    if info is None:
        info = get_system_info()

    # Explicit profile from settings / caller
    if profile and profile in ("standard", "high", "minimal"):
        base = SAFE_MODELS[profile].copy()
        base["tier"] = profile
        base["profile_source"] = "explicit"
        return base

    ram = info.get("ram_total_gb", 8)
    vram = info.get("total_vram_gb", 0)
    has_gpu = info.get("has_gpu", False)

    if has_gpu and vram >= 20:
        tier = "max"
    elif has_gpu and vram >= 10:
        tier = "high"
    elif has_gpu and vram >= 6:
        tier = "standard"
    elif ram >= 32:
        tier = "high"
    elif ram >= 16:
        tier = "standard"
    elif ram >= 8:
        tier = "standard"  # still prefer 7B; phi3 is fallback
    else:
        tier = "minimal"

    base = SAFE_MODELS[tier].copy()
    base["tier"] = tier
    base["profile_source"] = "auto-detected"
    return base


def resolve_model(settings_obj, info: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Final model choice:
    1. Explicit DEFAULT_MODEL env if set
    2. Else PROFILE (standard/high/minimal)
    3. Else auto from hardware
    """
    info = info or get_system_info()
    if getattr(settings_obj, "default_model", None) and settings_obj.default_model.strip():
        rec = recommend_model(info, profile=None)
        return {
            "recommended": settings_obj.default_model.strip(),
            "fallback": (settings_obj.fallback_model or rec["fallback"]).strip(),
            "reason": "Explicit DEFAULT_MODEL from environment",
            "tier": "override",
            "profile_source": "env",
        }

    profile = getattr(settings_obj, "profile", "auto") or "auto"
    if profile == "auto":
        return recommend_model(info)
    return recommend_model(info, profile=profile)
