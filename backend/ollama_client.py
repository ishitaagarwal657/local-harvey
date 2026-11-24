"""
Strict local-only Ollama client.
- Refuses any non-localhost host
- Never falls back to cloud
- Uses format:json when requesting structured output
- Applies hardware-recommended / profile model
- Logs every call
"""
import hashlib
import time
import json
import re
from typing import Optional, Dict, Any, List
import httpx
from .config import settings
from .database import log_inference
from .hardware import resolve_model, get_system_info


class LocalLLMError(Exception):
    """Raised when local inference fails. Never silently switches to cloud."""
    pass


def _extract_json(text: str) -> Any:
    """Best-effort extract of a JSON object/array from model output."""
    text = text.strip()
    if text.startswith("```"):
        # strip markdown fences
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.lstrip().startswith("json"):
                text = text.lstrip()[4:]
        text = text.strip()

    # Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find first { ... } or [ ... ]
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise json.JSONDecodeError("Could not extract JSON", text, 0)


class OllamaClient:
    def __init__(self):
        host = settings.ollama_host.rstrip("/")
        if not (host.startswith("http://127.0.0.1") or host.startswith("http://localhost")):
            raise LocalLLMError(
                f"SECURITY: Ollama host must be local (127.0.0.1 or localhost). "
                f"Got: {host}. Cloud endpoints are forbidden."
            )
        self.host = host
        self.timeout = settings.ollama_timeout
        self._resolved: Optional[Dict[str, Any]] = None

    def _model_choice(self) -> Dict[str, Any]:
        if self._resolved is None:
            self._resolved = resolve_model(settings, get_system_info())
        return self._resolved

    @property
    def default_model(self) -> str:
        return self._model_choice()["recommended"]

    @property
    def fallback_model(self) -> str:
        return self._model_choice()["fallback"]

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.host}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(f"{self.host}/api/tags")
                r.raise_for_status()
                data = r.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            raise LocalLLMError(f"Cannot list Ollama models: {e}")

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        agent: str = "unknown",
        temperature: float = 0.4,
        max_tokens: int = 2048,
        force_json: bool = False,
    ) -> Dict[str, Any]:
        model = model or self.default_model
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        start = time.time()

        if "127.0.0.1" not in self.host and "localhost" not in self.host:
            raise LocalLLMError("Refusing non-local Ollama host")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if force_json:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(f"{self.host}/api/chat", json=payload)
                r.raise_for_status()
                data = r.json()

            content = data.get("message", {}).get("content", "") or data.get("response", "")
            latency = int((time.time() - start) * 1000)
            await log_inference(agent, model, prompt_hash, latency, True)
            return {
                "content": content.strip(),
                "model": model,
                "latency_ms": latency,
                "prompt_hash": prompt_hash,
                "raw": data,
            }
        except httpx.ConnectError:
            latency = int((time.time() - start) * 1000)
            await log_inference(agent, model, prompt_hash, latency, False, "Ollama not reachable")
            raise LocalLLMError(
                "Ollama is not running or not reachable at 127.0.0.1:11434.\n"
                "Start it with: ollama serve\n"
                "Then pull a model: ollama pull qwen2.5:7b-instruct\n"
                "NO cloud fallback is allowed. Task may be queued for later."
            )
        except httpx.HTTPStatusError as e:
            # Model not found → try fallback once
            if e.response.status_code == 404 and model != self.fallback_model:
                return await self.generate(
                    prompt, system=system, model=self.fallback_model,
                    agent=agent, temperature=temperature, max_tokens=max_tokens,
                    force_json=force_json,
                )
            latency = int((time.time() - start) * 1000)
            await log_inference(agent, model, prompt_hash, latency, False, str(e))
            raise LocalLLMError(f"Local inference failed: {e}")
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            await log_inference(agent, model, prompt_hash, latency, False, str(e))
            raise LocalLLMError(f"Local inference failed: {e}")

    async def generate_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        agent: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Request JSON output via Ollama format=json + soft retries.
        Never crashes the API with an unhandled JSONDecodeError.
        """
        system_json = (system or "") + "\n\nYou MUST respond with valid JSON only. No markdown fences, no commentary."
        last_error = None

        for attempt, temp in enumerate((0.2, 0.1, 0.0)):
            try:
                result = await self.generate(
                    prompt if attempt == 0 else prompt + "\n\nReturn ONLY valid JSON. No other text.",
                    system=system_json,
                    model=model,
                    agent=agent,
                    temperature=temp,
                    force_json=True,
                )
                parsed = _extract_json(result["content"])
                result["parsed"] = parsed
                return result
            except (json.JSONDecodeError, LocalLLMError) as e:
                last_error = e
                continue

        raise LocalLLMError(
            f"Local model did not return valid JSON after retries. Last error: {last_error}"
        )


# Singleton
llm = OllamaClient()
